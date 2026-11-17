"""Hardware catalog: a non-exhaustive list of common hardware for new stock items.

The "Nom" field of a new item offers these names; picking one fills in the
other fields (category, value, package, reference, linked sheet). An entry's id
is also the id of its sheet when one exists (sheets/<id>.md): the item is then
linked to it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import yaml

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
URL_RE = re.compile(r"^https?://\S+$")
CORRECTION_TEMPLATE = "correction-fiche.yml"


def correction_url(repository: str, sheet_id: str, sheet_name: str) -> str:
    """Link to the GitHub form that reports an error in an existing sheet, pre-filled."""
    params = {"template": CORRECTION_TEMPLATE, "title": f"Correction : {sheet_name}", "sheet": sheet_id}
    return f"{repository}/issues/new?{urlencode(params, quote_via=quote)}"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _texts(value: Any) -> list[str]:
    items = value if isinstance(value, list) else ([value] if value else [])
    return [_text(item) for item in items if _text(item)]


def normalize(raw: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Valid entries of the catalog, and the problems found in the others."""
    devices, problems, seen = [], [], set()
    entries = raw.get("devices") if isinstance(raw, dict) else None
    for i, entry in enumerate(entries or []):
        if not isinstance(entry, dict):
            problems.append(f"devices[{i}]: not a mapping")
            continue
        device_id, name, category = _text(entry.get("id")), _text(entry.get("name")), _text(entry.get("category"))
        links = _texts(entry.get("links"))
        if not ID_RE.fullmatch(device_id) or device_id in seen:
            problems.append(f"devices[{i}]: missing, invalid or duplicate id '{device_id}'")
            continue
        if not name or not category:
            problems.append(f"{device_id}: name and category are required")
            continue
        if not all(URL_RE.fullmatch(link) for link in links):
            problems.append(f"{device_id}: links must be http(s) URLs")
            continue
        seen.add(device_id)
        devices.append({
            "id": device_id,
            "name": name,
            "category": category,
            "manufacturer": _text(entry.get("manufacturer")),
            "part_number": _text(entry.get("part_number")),
            "package": _text(entry.get("package")),
            "value": _text(entry.get("value")),
            "values": _texts(entry.get("values")),  # suggestions for the value field
            "description": _text(entry.get("description")),
            "dimensions": _text(entry.get("dimensions")),
            "links": links,
        })
    return devices, problems


class Catalog:
    """The catalog file (sheets/catalog.yaml), re-read when it changes."""

    def __init__(self, path: Path):
        self.path = path
        self._cache: tuple[float, list[dict[str, Any]]] | None = None

    def devices(self) -> list[dict[str, Any]]:
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            return []
        if self._cache is None or self._cache[0] != mtime:
            try:
                raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                raw = None
            self._cache = (mtime, normalize(raw)[0])
        return self._cache[1]
