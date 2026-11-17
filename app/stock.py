"""Stock : articles et historique des mouvements, dans une base SQLite."""

from __future__ import annotations

import csv
import io
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY,
    nom         TEXT    NOT NULL,
    categorie   TEXT    NOT NULL DEFAULT '',
    valeur      TEXT    NOT NULL DEFAULT '',
    boitier     TEXT    NOT NULL DEFAULT '',
    fiche       TEXT,
    quantite    INTEGER NOT NULL DEFAULT 0 CHECK (quantite >= 0),
    seuil       INTEGER NOT NULL DEFAULT 0 CHECK (seuil >= 0),
    emplacement TEXT    NOT NULL DEFAULT '',
    fournisseur TEXT    NOT NULL DEFAULT '',
    prix        REAL,
    notes       TEXT    NOT NULL DEFAULT '',
    cree        TEXT    NOT NULL,
    modifie     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS articles_fiche ON articles(fiche);
CREATE TABLE IF NOT EXISTS mouvements (
    id       INTEGER PRIMARY KEY,
    article  INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    delta    INTEGER NOT NULL,
    quantite INTEGER NOT NULL,
    motif    TEXT    NOT NULL DEFAULT '',
    date     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS mouvements_article ON mouvements(article, id);
"""

CHAMPS = ("nom", "categorie", "valeur", "boitier", "fiche", "quantite", "seuil",
          "emplacement", "fournisseur", "prix", "notes")
CHAMPS_CSV = ("id",) + CHAMPS + ("modifie",)


class StockError(ValueError):
    """Opération de stock refusée."""


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Stock:
    def __init__(self, chemin: Path):
        self.chemin = chemin
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with self._connexion() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _connexion(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.chemin, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            with c:
                yield c
        finally:
            c.close()

    @staticmethod
    def _nettoyer(donnees: dict[str, Any], partiel: bool) -> dict[str, Any]:
        d = {k: donnees[k] for k in CHAMPS if k in donnees}
        if not partiel or "nom" in d:
            if not str(d.get("nom") or "").strip():
                raise StockError("Le nom est obligatoire.")
        for k in ("quantite", "seuil"):
            if k in d:
                try:
                    d[k] = int(d[k] or 0)
                except (TypeError, ValueError):
                    raise StockError(f"« {k} » doit être un nombre entier.") from None
                if d[k] < 0:
                    raise StockError(f"« {k} » ne peut pas être négatif.")
        if "prix" in d:
            if d["prix"] in (None, ""):
                d["prix"] = None
            else:
                try:
                    d["prix"] = float(str(d["prix"]).replace(",", "."))
                except ValueError:
                    raise StockError("Le prix doit être un nombre.") from None
        if "fiche" in d:
            d["fiche"] = str(d["fiche"] or "").strip() or None
        for k in ("nom", "categorie", "valeur", "boitier", "emplacement", "fournisseur", "notes"):
            if k in d:
                d[k] = str(d[k] or "").strip()
        return d

    def lister(self, q: str = "", categorie: str = "", fiche: str = "", alerte: bool = False) -> list[dict]:
        sql = "SELECT * FROM articles WHERE 1=1"
        args: list[Any] = []
        if q:
            sql += (" AND (nom LIKE ? OR valeur LIKE ? OR boitier LIKE ? OR emplacement LIKE ?"
                    " OR notes LIKE ? OR categorie LIKE ? OR fiche LIKE ?)")
            args += [f"%{q}%"] * 7
        if categorie:
            sql += " AND categorie = ?"
            args.append(categorie)
        if fiche:
            sql += " AND fiche = ?"
            args.append(fiche)
        if alerte:
            sql += " AND quantite <= seuil"
        sql += " ORDER BY categorie COLLATE NOCASE, nom COLLATE NOCASE, valeur COLLATE NOCASE"
        with self._connexion() as c:
            return [dict(r) for r in c.execute(sql, args)]

    def lire(self, id_: int) -> dict:
        with self._connexion() as c:
            r = c.execute("SELECT * FROM articles WHERE id = ?", (id_,)).fetchone()
        if r is None:
            raise KeyError(id_)
        return dict(r)

    def creer(self, donnees: dict[str, Any]) -> dict:
        d = self._nettoyer(donnees, partiel=False)
        t = maintenant()
        d.update(cree=t, modifie=t)
        cles = ", ".join(d)
        with self._connexion() as c:
            cur = c.execute(f"INSERT INTO articles ({cles}) VALUES ({', '.join('?' * len(d))})", list(d.values()))
            id_ = cur.lastrowid
            if d.get("quantite"):
                c.execute("INSERT INTO mouvements (article, delta, quantite, motif, date) VALUES (?, ?, ?, ?, ?)",
                          (id_, d["quantite"], d["quantite"], "Création", t))
        return self.lire(id_)

    def modifier(self, id_: int, donnees: dict[str, Any]) -> dict:
        ancien = self.lire(id_)
        d = self._nettoyer(donnees, partiel=True)
        if not d:
            return ancien
        t = maintenant()
        d["modifie"] = t
        with self._connexion() as c:
            c.execute(f"UPDATE articles SET {', '.join(f'{k} = ?' for k in d)} WHERE id = ?", [*d.values(), id_])
            if "quantite" in d and d["quantite"] != ancien["quantite"]:
                c.execute("INSERT INTO mouvements (article, delta, quantite, motif, date) VALUES (?, ?, ?, ?, ?)",
                          (id_, d["quantite"] - ancien["quantite"], d["quantite"], "Correction d'inventaire", t))
        return self.lire(id_)

    def supprimer(self, id_: int) -> None:
        with self._connexion() as c:
            if c.execute("DELETE FROM articles WHERE id = ?", (id_,)).rowcount == 0:
                raise KeyError(id_)

    def mouvement(self, id_: int, delta: int, motif: str = "") -> dict:
        if not isinstance(delta, int) or delta == 0:
            raise StockError("La variation doit être un entier non nul.")
        t = maintenant()
        with self._connexion() as c:
            r = c.execute("SELECT quantite FROM articles WHERE id = ?", (id_,)).fetchone()
            if r is None:
                raise KeyError(id_)
            nouvelle = r["quantite"] + delta
            if nouvelle < 0:
                raise StockError(f"Stock insuffisant : {r['quantite']} en stock.")
            c.execute("UPDATE articles SET quantite = ?, modifie = ? WHERE id = ?", (nouvelle, t, id_))
            c.execute("INSERT INTO mouvements (article, delta, quantite, motif, date) VALUES (?, ?, ?, ?, ?)",
                      (id_, delta, nouvelle, motif.strip(), t))
        return self.lire(id_)

    def historique(self, id_: int, limite: int = 100) -> list[dict]:
        self.lire(id_)
        with self._connexion() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM mouvements WHERE article = ? ORDER BY id DESC LIMIT ?", (id_, limite))]

    def categories(self) -> list[str]:
        with self._connexion() as c:
            return [r[0] for r in c.execute(
                "SELECT DISTINCT categorie FROM articles WHERE categorie <> '' ORDER BY categorie COLLATE NOCASE")]

    def resume(self) -> dict[str, int]:
        with self._connexion() as c:
            r = c.execute("SELECT COUNT(*), COALESCE(SUM(quantite), 0), "
                          "COALESCE(SUM(quantite <= seuil), 0) FROM articles").fetchone()
        return {"articles": r[0], "pieces": r[1], "alertes": r[2]}

    def exporter_csv(self) -> str:
        sortie = io.StringIO()
        w = csv.DictWriter(sortie, fieldnames=CHAMPS_CSV, extrasaction="ignore", delimiter=";")
        w.writeheader()
        for a in self.lister():
            w.writerow(a)
        return sortie.getvalue()

    def importer_csv(self, texte: str) -> dict[str, int]:
        """Crée ou met à jour (si la colonne id correspond) chaque ligne du CSV."""
        texte = texte.lstrip("﻿")
        dialecte = csv.Sniffer().sniff(texte.split("\n", 1)[0], delimiters=";,\t")
        crees = maj = 0
        for i, ligne in enumerate(csv.DictReader(io.StringIO(texte), dialect=dialecte), start=2):
            ligne = {k.strip().lower(): v for k, v in ligne.items() if k}
            id_ = (ligne.pop("id", "") or "").strip()
            try:
                if id_.isdigit():
                    try:
                        self.lire(int(id_))
                        self.modifier(int(id_), ligne)
                        maj += 1
                        continue
                    except KeyError:
                        pass
                self.creer(ligne)
                crees += 1
            except StockError as exc:
                raise StockError(f"Ligne {i} : {exc}") from None
        return {"crees": crees, "mis_a_jour": maj}
