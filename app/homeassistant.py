"""Publication de l'état du stock dans Home Assistant, sous forme de capteurs.

Deux modes :
- module complémentaire (add-on) : la variable SUPERVISOR_TOKEN est fournie par le
  Supervisor, l'API de Home Assistant est jointe via http://supervisor/core ;
- conteneur indépendant : PROMETHEE_HA_URL (ex. http://192.168.1.10:8123) et
  PROMETHEE_HA_TOKEN (jeton d'accès longue durée).

Les capteurs sont réécrits après chaque modification du stock et toutes les
cinq minutes, car Home Assistant oublie ces états à son redémarrage.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
from typing import Any, Callable

log = logging.getLogger("promethee.homeassistant")

PERIODE = 300  # secondes
MAX_ARTICLES_ATTRIBUT = 50


def configuration() -> tuple[str, str] | None:
    """Retourne (url de base de l'API, jeton), ou None si l'intégration est désactivée."""
    if os.environ.get("PROMETHEE_HA", "").lower() in {"0", "non", "false", "off"}:
        return None
    jeton = os.environ.get("SUPERVISOR_TOKEN")
    if jeton:
        return "http://supervisor/core/api", jeton
    url, jeton = os.environ.get("PROMETHEE_HA_URL"), os.environ.get("PROMETHEE_HA_TOKEN")
    if url and jeton:
        return url.rstrip("/") + "/api", jeton
    return None


def etats(resume: dict[str, Any], alertes: list[dict[str, Any]], url_interface: str = "") -> dict[str, dict]:
    """Construit les états des capteurs à partir du stock."""
    commun = {"attribution": "Prométhée"}
    if url_interface:
        commun["url"] = url_interface
    return {
        "sensor.promethee_references": {
            "state": resume["articles"],
            "attributes": {**commun, "friendly_name": "Prométhée références", "icon": "mdi:archive-outline",
                           "unit_of_measurement": "références", "state_class": "measurement"},
        },
        "sensor.promethee_pieces": {
            "state": resume["pieces"],
            "attributes": {**commun, "friendly_name": "Prométhée pièces en stock", "icon": "mdi:chip",
                           "unit_of_measurement": "pièces", "state_class": "measurement"},
        },
        "sensor.promethee_alertes": {
            "state": resume["alertes"],
            "attributes": {
                **commun,
                "friendly_name": "Prométhée à réapprovisionner",
                "icon": "mdi:alert-circle-outline" if resume["alertes"] else "mdi:check-circle-outline",
                "unit_of_measurement": "articles",
                "state_class": "measurement",
                "articles": [
                    {k: a[k] for k in ("nom", "valeur", "quantite", "seuil", "emplacement")}
                    for a in alertes[:MAX_ARTICLES_ATTRIBUT]
                ],
            },
        },
        "sensor.promethee_fiches": {
            "state": resume["fiches"],
            "attributes": {**commun, "friendly_name": "Prométhée fiches techniques", "icon": "mdi:book-open-variant",
                           "unit_of_measurement": "fiches"},
        },
    }


class Publieur:
    """Fil d'arrière-plan qui pousse les capteurs, sans bloquer les requêtes."""

    def __init__(self, source: Callable[[], dict[str, dict]], config: tuple[str, str] | None = None):
        self.source = source
        self.config = config if config is not None else configuration()
        self._evenement = threading.Event()
        self._arret = threading.Event()
        self._fil: threading.Thread | None = None
        self._erreur_signalee = False

    @property
    def actif(self) -> bool:
        return self.config is not None

    def demarrer(self) -> None:
        if not self.actif or self._fil:
            return
        self._fil = threading.Thread(target=self._boucle, name="promethee-ha", daemon=True)
        self._fil.start()
        log.info("Publication des capteurs vers Home Assistant activée.")

    def arreter(self) -> None:
        self._arret.set()
        self._evenement.set()

    def signaler(self) -> None:
        """Demande une publication (après une modification du stock)."""
        self._evenement.set()

    def publier(self) -> None:
        if not self.config:
            return
        base, jeton = self.config
        for entite, etat in self.source().items():
            requete = urllib.request.Request(
                f"{base}/states/{entite}",
                data=json.dumps(etat).encode(),
                headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(requete, timeout=10):
                pass

    def _boucle(self) -> None:
        while not self._arret.is_set():
            try:
                self.publier()
                if self._erreur_signalee:
                    log.info("Home Assistant joint à nouveau.")
                self._erreur_signalee = False
            except Exception as exc:  # réseau, jeton refusé, HA en redémarrage…
                if not self._erreur_signalee:
                    log.warning("Publication vers Home Assistant impossible : %s", exc)
                self._erreur_signalee = True
            self._evenement.wait(PERIODE)
            self._evenement.clear()
            self._arret.wait(1)  # regroupe les modifications rapprochées
