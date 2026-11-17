"""Fiches d'appareils : un fichier Markdown avec en-tête YAML par appareil.

Le format est décrit dans docs/format-fiche.md. Les fichiers dont le nom
commence par « _ » (le modèle vierge, par exemple) ne sont pas listés.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import markdown
import yaml

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(.*)\Z", re.S)

TYPES_BROCHE = {
    "alim", "masse", "gpio", "analogique", "pwm", "i2c", "spi", "uart",
    "controle", "reserve", "nc", "autre",
}
TYPES_BOITIER = {"carte", "module", "dip", "to92"}
COTES = {"gauche", "droite", "haut", "bas"}
EXTENSIONS_MODELE = {".glb", ".gltf", ".stl"}


class _Loader(yaml.SafeLoader):
    """YAML sûr où seuls true/false sont des booléens.

    En YAML 1.1, « ON », « NO » ou « Y » deviennent des booléens, ce qui
    transformerait silencieusement des noms de broches.
    """


_Loader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


class FicheError(ValueError):
    """Fiche illisible ou invalide."""


@dataclass
class Fiche:
    id: str
    meta: dict[str, Any]
    corps: str
    source: str
    avertissements: list[str] = field(default_factory=list)

    def resume(self) -> dict[str, Any]:
        m = self.meta
        return {
            "id": self.id,
            "nom": m["nom"],
            "categorie": m["categorie"],
            "fabricant": m["fabricant"],
            "reference": m["reference"],
            "description": m["description"],
            "tags": m["tags"],
            "nb_broches": sum(len(r["broches"]) for r in m["brochage"]["rangees"]),
            "modele3d": bool(m["modele3d"]),
        }

    def complete(self) -> dict[str, Any]:
        html = markdown.markdown(
            self.corps,
            extensions=["tables", "fenced_code", "sane_lists", "toc", "attr_list"],
            output_format="html",
        )
        return {**self.meta, "id": self.id, "html": html, "source": self.source,
                "avertissements": self.avertissements}


def _texte(valeur: Any) -> str:
    if valeur is None:
        return ""
    return str(valeur).strip()


def _nombre(valeur: Any, defaut: float, nom: str, avert: list[str]) -> float:
    if valeur is None or valeur == "":
        return defaut
    try:
        n = float(valeur)
    except (TypeError, ValueError):
        avert.append(f"{nom} : « {valeur} » n'est pas un nombre, {defaut} utilisé.")
        return defaut
    if n <= 0:
        avert.append(f"{nom} : doit être positif, {defaut} utilisé.")
        return defaut
    return n


def _optionnel(valeur: Any) -> float | None:
    try:
        return None if valeur is None or valeur == "" else float(valeur)
    except (TypeError, ValueError):
        return None


def decouper(source: str) -> tuple[dict[str, Any], str]:
    """Sépare l'en-tête YAML du corps Markdown."""
    source = source.lstrip("﻿")
    m = FRONT_MATTER_RE.match(source)
    if not m:
        raise FicheError("L'en-tête YAML est absent : la fiche doit commencer par une ligne « --- ».")
    try:
        meta = yaml.load(m.group(1), Loader=_Loader) or {}
    except yaml.YAMLError as exc:
        raise FicheError(f"En-tête YAML invalide : {exc}") from exc
    if not isinstance(meta, dict):
        raise FicheError("L'en-tête YAML doit être une suite de clés « nom: valeur ».")
    return meta, m.group(2)


def _normaliser_boitier(brut: Any, avert: list[str]) -> dict[str, Any]:
    b = brut if isinstance(brut, dict) else {}
    type_ = _texte(b.get("type")).lower() or "carte"
    if type_ not in TYPES_BOITIER:
        avert.append(f"boitier.type : « {type_} » inconnu (attendu : {', '.join(sorted(TYPES_BOITIER))}), « carte » utilisé.")
        type_ = "carte"
    defauts = {
        "carte": (50.0, 25.0, 1.6, "#1d5c3a"),
        "module": (20.0, 15.0, 1.6, "#1b3f8f"),
        "dip": (10.16, 7.62, 3.3, "#1b1d22"),
        "to92": (3.8, 4.8, 4.8, "#1b1d22"),
    }[type_]
    couleur = _texte(b.get("couleur")) or defauts[3]
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", couleur):
        avert.append(f"boitier.couleur : « {couleur} » doit s'écrire #rrggbb.")
        couleur = defauts[3]
    return {
        "type": type_,
        "longueur": _nombre(b.get("longueur"), defauts[0], "boitier.longueur", avert),
        "largeur": _nombre(b.get("largeur"), defauts[1], "boitier.largeur", avert),
        "epaisseur": _nombre(b.get("epaisseur"), defauts[2], "boitier.epaisseur", avert),
        "couleur": couleur,
        "marquage": _texte(b.get("marquage")),
    }


def _normaliser_brochage(brut: Any, boitier: dict[str, Any], avert: list[str]) -> dict[str, Any]:
    b = brut if isinstance(brut, dict) else {}
    pas = _nombre(b.get("pas"), 1.27 if boitier["type"] == "to92" else 2.54, "brochage.pas", avert)
    retrait_defaut = 0.0 if boitier["type"] in {"dip", "to92"} else 1.27
    rangees = []
    for i, r in enumerate(b.get("rangees") or []):
        if not isinstance(r, dict):
            avert.append(f"brochage.rangees[{i}] ignorée : ce doit être un objet.")
            continue
        cote = _texte(r.get("cote")).lower() or "gauche"
        if cote not in COTES:
            avert.append(f"brochage.rangees[{i}].cote : « {cote} » inconnu, « gauche » utilisé.")
            cote = "gauche"
        broches = []
        for j, p in enumerate(r.get("broches") or []):
            if not isinstance(p, dict):
                p = {"nom": p}
            type_ = _texte(p.get("type")).lower() or "autre"
            if type_ not in TYPES_BROCHE:
                avert.append(f"Broche « {_texte(p.get('nom'))} » : type « {type_} » inconnu, « autre » utilisé.")
                type_ = "autre"
            fonctions = p.get("fonctions") or []
            if not isinstance(fonctions, list):
                fonctions = [fonctions]
            broches.append({
                "n": _texte(p.get("n")) or str(j + 1),
                "nom": _texte(p.get("nom")) or "?",
                "type": type_,
                "fonctions": [_texte(f) for f in fonctions if _texte(f)],
                "desc": _texte(p.get("desc")),
            })
        rangees.append({
            "nom": _texte(r.get("nom")) or f"R{i + 1}",
            "cote": cote,
            "pas": _nombre(r.get("pas"), pas, f"brochage.rangees[{i}].pas", avert),
            "retrait": retrait_defaut if _optionnel(r.get("retrait")) is None else _optionnel(r.get("retrait")),
            "debut": _optionnel(r.get("debut")),
            "broches": broches,
        })
    return {"pas": pas, "rangees": rangees}


def _normaliser_composants(brut: Any, avert: list[str]) -> list[dict[str, Any]]:
    composants = []
    for i, c in enumerate(brut or []):
        if not isinstance(c, dict):
            avert.append(f"composants[{i}] ignoré : ce doit être un objet.")
            continue
        couleur = _texte(c.get("couleur")) or "#2a2d34"
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", couleur):
            couleur = "#2a2d34"
        composants.append({
            "nom": _texte(c.get("nom")),
            "x": _optionnel(c.get("x")) or 0.0,
            "y": _optionnel(c.get("y")) or 0.0,
            "largeur": _nombre(c.get("largeur"), 3, f"composants[{i}].largeur", avert),
            "longueur": _nombre(c.get("longueur"), 3, f"composants[{i}].longueur", avert),
            "hauteur": _nombre(c.get("hauteur"), 1, f"composants[{i}].hauteur", avert),
            "couleur": couleur,
            "texte": _texte(c.get("texte")),
            "forme": "cylindre" if _texte(c.get("forme")).lower() == "cylindre" else "boite",
        })
    return composants


def normaliser(meta: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Valide l'en-tête et complète les valeurs par défaut."""
    avert: list[str] = []
    nom = _texte(meta.get("nom"))
    if not nom:
        raise FicheError("Le champ « nom » est obligatoire.")
    tags = meta.get("tags") or []
    if not isinstance(tags, list):
        tags = [t.strip() for t in str(tags).split(",")]
    specs = meta.get("caracteristiques") or {}
    if not isinstance(specs, dict):
        avert.append("caracteristiques : doit être une liste « clé: valeur ».")
        specs = {}
    liens = meta.get("liens") or []
    if isinstance(liens, dict):
        liens = [{"titre": k, "url": v} for k, v in liens.items()]
    liens = [
        {"titre": _texte(l.get("titre")) or _texte(l.get("url")), "url": _texte(l.get("url"))}
        for l in liens if isinstance(l, dict) and _texte(l.get("url"))
    ]
    modele3d = _texte(meta.get("modele3d"))
    if modele3d and Path(modele3d).suffix.lower() not in EXTENSIONS_MODELE:
        avert.append(f"modele3d : format non pris en charge ({', '.join(sorted(EXTENSIONS_MODELE))}).")
        modele3d = ""
    boitier = _normaliser_boitier(meta.get("boitier"), avert)
    return {
        "nom": nom,
        "categorie": _texte(meta.get("categorie")) or "Divers",
        "fabricant": _texte(meta.get("fabricant")),
        "reference": _texte(meta.get("reference")),
        "description": _texte(meta.get("description")),
        "tags": [_texte(t) for t in tags if _texte(t)],
        "caracteristiques": {_texte(k): _texte(v) for k, v in specs.items()},
        "liens": liens,
        "modele3d": modele3d,
        "boitier": boitier,
        "brochage": _normaliser_brochage(meta.get("brochage"), boitier, avert),
        "composants": _normaliser_composants(meta.get("composants"), avert),
    }, avert


def analyser(id_: str, source: str) -> Fiche:
    meta, corps = decouper(source)
    meta_norm, avert = normaliser(meta)
    return Fiche(id=id_, meta=meta_norm, corps=corps, source=source, avertissements=avert)


def verifier_id(id_: str) -> str:
    if not ID_RE.fullmatch(id_ or ""):
        raise FicheError("Identifiant invalide : lettres minuscules, chiffres et tirets (64 caractères au plus).")
    return id_


def slug(texte: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:64] or "fiche"


class Bibliotheque:
    """Accès au dossier des fiches. Relit les fichiers modifiés à chaque appel."""

    def __init__(self, dossier: Path):
        self.dossier = dossier
        self._cache: dict[str, tuple[float, Fiche | FicheError]] = {}

    @property
    def dossier_modeles(self) -> Path:
        return self.dossier / "modeles"

    def chemin(self, id_: str) -> Path:
        return self.dossier / f"{verifier_id(id_)}.md"

    def _charger(self, chemin: Path) -> Fiche | FicheError:
        id_ = chemin.stem
        mtime = chemin.stat().st_mtime
        cache = self._cache.get(id_)
        if cache and cache[0] == mtime:
            return cache[1]
        try:
            resultat: Fiche | FicheError = analyser(id_, chemin.read_text(encoding="utf-8"))
        except (FicheError, UnicodeDecodeError) as exc:
            resultat = exc if isinstance(exc, FicheError) else FicheError(f"Encodage invalide : {exc}")
        self._cache[id_] = (mtime, resultat)
        return resultat

    def lister(self) -> tuple[list[Fiche], list[dict[str, str]]]:
        fiches, erreurs = [], []
        if not self.dossier.is_dir():
            return fiches, erreurs
        for chemin in sorted(self.dossier.glob("*.md")):
            if chemin.name.startswith("_") or not ID_RE.fullmatch(chemin.stem):
                continue
            r = self._charger(chemin)
            if isinstance(r, Fiche):
                fiches.append(r)
            else:
                erreurs.append({"id": chemin.stem, "erreur": str(r)})
        fiches.sort(key=lambda f: (f.meta["categorie"].lower(), f.meta["nom"].lower()))
        return fiches, erreurs

    def lire(self, id_: str) -> Fiche:
        chemin = self.chemin(id_)
        if not chemin.is_file():
            raise FileNotFoundError(id_)
        r = self._charger(chemin)
        if isinstance(r, FicheError):
            raise r
        return r

    def source(self, id_: str) -> str:
        chemin = self.chemin(id_)
        if not chemin.is_file():
            raise FileNotFoundError(id_)
        return chemin.read_text(encoding="utf-8")

    def existe(self, id_: str) -> bool:
        return self.chemin(id_).is_file()

    def ecrire(self, id_: str, source: str) -> Fiche:
        fiche = analyser(verifier_id(id_), source)  # refuse d'écrire une fiche invalide
        self.dossier.mkdir(parents=True, exist_ok=True)
        _ecriture_atomique(self.chemin(id_), source.replace("\r\n", "\n").encode("utf-8"))
        self._cache.pop(id_, None)
        return fiche

    def supprimer(self, id_: str) -> None:
        chemin = self.chemin(id_)
        if not chemin.is_file():
            raise FileNotFoundError(id_)
        chemin.unlink()
        self._cache.pop(id_, None)

    def chemin_modele(self, nom: str) -> Path:
        """Résout un modèle 3D en refusant toute sortie du dossier modeles/."""
        nom = nom.removeprefix("modeles/")
        chemin = (self.dossier_modeles / nom).resolve()
        if self.dossier_modeles.resolve() not in chemin.parents or chemin.suffix.lower() not in EXTENSIONS_MODELE:
            raise FileNotFoundError(nom)
        return chemin

    def ecrire_modele(self, nom: str, contenu: bytes) -> str:
        base = slug(Path(nom).stem)
        ext = Path(nom).suffix.lower()
        if ext not in EXTENSIONS_MODELE:
            raise FicheError(f"Format non pris en charge ({', '.join(sorted(EXTENSIONS_MODELE))}).")
        self.dossier_modeles.mkdir(parents=True, exist_ok=True)
        _ecriture_atomique(self.dossier_modeles / f"{base}{ext}", contenu)
        return f"modeles/{base}{ext}"


def _ecriture_atomique(chemin: Path, contenu: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=chemin.parent, prefix=".tmp-", suffix=chemin.suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(contenu)
        os.chmod(tmp, 0o644)
        os.replace(tmp, chemin)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
