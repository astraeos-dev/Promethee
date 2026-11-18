"""Inventory: items and their stock movement history, stored in SQLite.

"""

from __future__ import annotations

import csv
import io
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    category    TEXT    NOT NULL DEFAULT '',
    value       TEXT    NOT NULL DEFAULT '',
    package     TEXT    NOT NULL DEFAULT '',
    sheet       TEXT,
    quantity    INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    threshold   INTEGER NOT NULL DEFAULT 0 CHECK (threshold >= 0),
    location    TEXT    NOT NULL DEFAULT '',
    supplier    TEXT    NOT NULL DEFAULT '',
    price       REAL,
    notes       TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS items_sheet ON items(sheet);
CREATE TABLE IF NOT EXISTS movements (
    id          INTEGER PRIMARY KEY,
    item_id     INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    delta       INTEGER NOT NULL,
    quantity    INTEGER NOT NULL,
    reason      TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS movements_item ON movements(item_id, id);
"""

FIELDS = ("name", "category", "value", "package", "sheet", "quantity", "threshold",
          "location", "supplier", "price", "notes")
TEXT_FIELDS = ("name", "category", "value", "package", "location", "supplier", "notes")
CSV_FIELDS = ("id",) + FIELDS + ("updated_at",)

class InventoryError(ValueError):
    """Rejected inventory operation."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Inventory:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _clean(data: dict[str, Any], partial: bool) -> dict[str, Any]:
        d = {k: data[k] for k in FIELDS if k in data}
        if (not partial or "name" in d) and not str(d.get("name") or "").strip():
            raise InventoryError("Le nom est obligatoire.")
        for key, label in (("quantity", "quantité"), ("threshold", "seuil")):
            if key in d:
                try:
                    d[key] = int(d[key] or 0)
                except (TypeError, ValueError):
                    raise InventoryError(f"« {label} » doit être un nombre entier.") from None
                if d[key] < 0:
                    raise InventoryError(f"« {label} » ne peut pas être négatif.")
        if "price" in d:
            if d["price"] in (None, ""):
                d["price"] = None
            else:
                try:
                    d["price"] = float(str(d["price"]).replace(",", "."))
                except ValueError:
                    raise InventoryError("Le prix doit être un nombre.") from None
        if "sheet" in d:
            d["sheet"] = str(d["sheet"] or "").strip() or None
        for key in TEXT_FIELDS:
            if key in d:
                d[key] = str(d[key] or "").strip()
        return d

    def _log(self, conn: sqlite3.Connection, item_id: int, delta: int, quantity: int, reason: str, at: str) -> None:
        conn.execute(
            "INSERT INTO movements (item_id, delta, quantity, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (item_id, delta, quantity, reason, at),
        )

    def list(self, query: str = "", category: str = "", sheet: str = "", low_stock: bool = False) -> list[dict]:
        sql = "SELECT * FROM items WHERE 1=1"
        args: list[Any] = []
        if query:
            columns = ("name", "value", "package", "location", "notes", "category", "sheet")
            sql += " AND (" + " OR ".join(f"{c} LIKE ?" for c in columns) + ")"
            args += [f"%{query}%"] * len(columns)
        if category:
            sql += " AND category = ?"
            args.append(category)
        if sheet:
            sql += " AND sheet = ?"
            args.append(sheet)
        if low_stock:
            sql += " AND quantity <= threshold"
        sql += " ORDER BY category COLLATE NOCASE, name COLLATE NOCASE, value COLLATE NOCASE"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, args)]

    def get(self, item_id: int) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return dict(row)

    def create(self, data: dict[str, Any]) -> dict:
        d = self._clean(data, partial=False)
        at = now()
        d.update(created_at=at, updated_at=at)
        with self._connect() as conn:
            cur = conn.execute(
                f"INSERT INTO items ({', '.join(d)}) VALUES ({', '.join('?' * len(d))})", list(d.values()))
            item_id = cur.lastrowid
            if d.get("quantity"):
                self._log(conn, item_id, d["quantity"], d["quantity"], "Création", at)
        return self.get(item_id)

    def update(self, item_id: int, data: dict[str, Any]) -> dict:
        previous = self.get(item_id)
        d = self._clean(data, partial=True)
        if not d:
            return previous
        at = now()
        d["updated_at"] = at
        with self._connect() as conn:
            conn.execute(f"UPDATE items SET {', '.join(f'{k} = ?' for k in d)} WHERE id = ?", [*d.values(), item_id])
            if "quantity" in d and d["quantity"] != previous["quantity"]:
                self._log(conn, item_id, d["quantity"] - previous["quantity"], d["quantity"],
                          "Correction d'inventaire", at)
        return self.get(item_id)

    def delete(self, item_id: int) -> None:
        with self._connect() as conn:
            if conn.execute("DELETE FROM items WHERE id = ?", (item_id,)).rowcount == 0:
                raise KeyError(item_id)

    def move(self, item_id: int, delta: int, reason: str = "") -> dict:
        if not isinstance(delta, int) or delta == 0:
            raise InventoryError("La variation doit être un entier non nul.")
        at = now()
        with self._connect() as conn:
            row = conn.execute("SELECT quantity FROM items WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise KeyError(item_id)
            quantity = row["quantity"] + delta
            if quantity < 0:
                raise InventoryError(f"Stock insuffisant : {row['quantity']} en stock.")
            conn.execute("UPDATE items SET quantity = ?, updated_at = ? WHERE id = ?", (quantity, at, item_id))
            self._log(conn, item_id, delta, quantity, reason.strip(), at)
        return self.get(item_id)

    def history(self, item_id: int, limit: int = 100) -> list[dict]:
        self.get(item_id)
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM movements WHERE item_id = ? ORDER BY id DESC LIMIT ?", (item_id, limit))]

    def categories(self) -> list[str]:
        with self._connect() as conn:
            return [r[0] for r in conn.execute(
                "SELECT DISTINCT category FROM items WHERE category <> '' ORDER BY category COLLATE NOCASE")]

    def summary(self) -> dict[str, int]:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0), "
                               "COALESCE(SUM(quantity <= threshold), 0) FROM items").fetchone()
        return {"items": row[0], "parts": row[1], "low_stock": row[2]}

    def export_csv(self) -> str:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=CSV_FIELDS, extrasaction="ignore", delimiter=";")
        writer.writeheader()
        for item in self.list():
            writer.writerow(item)
        return out.getvalue()

    def import_csv(self, text: str) -> dict[str, int]:
        """Create each CSV row, or update it when its id column matches an item."""
        text = text.lstrip("﻿")
        dialect = csv.Sniffer().sniff(text.split("\n", 1)[0], delimiters=";,\t")
        created = updated = 0
        for line_no, row in enumerate(csv.DictReader(io.StringIO(text), dialect=dialect), start=2):
            row = {CSV_ALIASES.get(k.strip().lower(), k.strip().lower()): v for k, v in row.items() if k}
            item_id = (row.pop("id", "") or "").strip()
            try:
                if item_id.isdigit():
                    try:
                        self.update(int(item_id), row)
                        updated += 1
                        continue
                    except KeyError:
                        pass
                self.create(row)
                created += 1
            except InventoryError as exc:
                raise InventoryError(f"Ligne {line_no} : {exc}") from None
        return {"created": created, "updated": updated}
