"""Device sheets: one Markdown file with a YAML front matter per device.

The format is described in docs/sheet-format.md. Files whose name starts
with "_" (such as the blank template) are not listed.

Messages returned to the user (errors, warnings) are in French, like the UI.
"""

from __future__ import annotations

import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import markdown
import yaml

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(.*)\Z", re.S)
COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")

PIN_TYPES = {
    "power", "ground", "gpio", "analog", "pwm", "i2c", "spi", "uart",
    "control", "reserved", "nc", "other",
}
PACKAGE_TYPES = {"board", "module", "dip", "to92"}
SIDES = {"left", "right", "top", "bottom"}
MODEL_EXTENSIONS = {".glb", ".gltf", ".stl"}

# Default size (length, width, thickness in mm) and color per package type.
PACKAGE_DEFAULTS = {
    "board": (50.0, 25.0, 1.6, "#1d5c3a"),
    "module": (20.0, 15.0, 1.6, "#1b3f8f"),
    "dip": (10.16, 7.62, 3.3, "#1b1d22"),
    "to92": (3.8, 4.8, 4.8, "#1b1d22"),
}


class _Loader(yaml.SafeLoader):
    """Safe YAML loader where only true/false are booleans.

    YAML 1.1 turns "ON", "NO" or "Y" into booleans, which would silently
    change pin names.
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


class SheetError(ValueError):
    """Unreadable or invalid sheet."""


@dataclass
class Sheet:
    id: str
    meta: dict[str, Any]
    body: str
    source: str
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        m = self.meta
        return {
            "id": self.id,
            "name": m["name"],
            "category": m["category"],
            "manufacturer": m["manufacturer"],
            "part_number": m["part_number"],
            "description": m["description"],
            "tags": m["tags"],
            "pin_count": sum(len(r["pins"]) for r in m["pinout"]["rows"]),
            "has_model3d": bool(m["model3d"]),
        }

    def full(self) -> dict[str, Any]:
        html = markdown.markdown(
            self.body,
            extensions=["tables", "fenced_code", "sane_lists", "toc", "attr_list"],
            output_format="html",
        )
        return {**self.meta, "id": self.id, "html": html, "source": self.source, "warnings": self.warnings}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _positive(value: Any, default: float, key: str, warnings: list[str]) -> float:
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        warnings.append(f"{key} : « {value} » n'est pas un nombre, {default} utilisé.")
        return default
    if number <= 0:
        warnings.append(f"{key} : doit être positif, {default} utilisé.")
        return default
    return number


def _optional_float(value: Any) -> float | None:
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None


def _color(value: Any, default: str, key: str, warnings: list[str]) -> str:
    color = _text(value) or default
    if not COLOR_RE.fullmatch(color):
        warnings.append(f"{key} : « {color} » doit s'écrire #rrggbb.")
        return default
    return color


def split_front_matter(source: str) -> tuple[dict[str, Any], str]:
    """Split the YAML front matter from the Markdown body."""
    source = source.lstrip("﻿")
    match = FRONT_MATTER_RE.match(source)
    if not match:
        raise SheetError("L'en-tête YAML est absent : la fiche doit commencer par une ligne « --- ».")
    try:
        meta = yaml.load(match.group(1), Loader=_Loader) or {}
    except yaml.YAMLError as exc:
        raise SheetError(f"En-tête YAML invalide : {exc}") from exc
    if not isinstance(meta, dict):
        raise SheetError("L'en-tête YAML doit être une suite de clés « nom: valeur ».")
    return meta, match.group(2)


def _normalize_package(raw: Any, warnings: list[str]) -> dict[str, Any]:
    pkg = raw if isinstance(raw, dict) else {}
    kind = _text(pkg.get("type")).lower() or "board"
    if kind not in PACKAGE_TYPES:
        warnings.append(f"package.type : « {kind} » inconnu (attendu : {', '.join(sorted(PACKAGE_TYPES))}), « board » utilisé.")
        kind = "board"
    length, width, thickness, color = PACKAGE_DEFAULTS[kind]
    return {
        "type": kind,
        "length": _positive(pkg.get("length"), length, "package.length", warnings),
        "width": _positive(pkg.get("width"), width, "package.width", warnings),
        "thickness": _positive(pkg.get("thickness"), thickness, "package.thickness", warnings),
        "color": _color(pkg.get("color"), color, "package.color", warnings),
        "marking": _text(pkg.get("marking")),
    }


def _normalize_pin(raw: Any, index: int, warnings: list[str]) -> dict[str, Any]:
    pin = raw if isinstance(raw, dict) else {"name": raw}
    kind = _text(pin.get("type")).lower() or "other"
    if kind not in PIN_TYPES:
        warnings.append(f"Broche « {_text(pin.get('name'))} » : type « {kind} » inconnu, « other » utilisé.")
        kind = "other"
    functions = pin.get("functions") or []
    if not isinstance(functions, list):
        functions = [functions]
    return {
        "n": _text(pin.get("n")) or str(index + 1),
        "name": _text(pin.get("name")) or "?",
        "type": kind,
        "functions": [_text(f) for f in functions if _text(f)],
        "description": _text(pin.get("description")),
    }


def _normalize_pinout(raw: Any, package: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    pinout = raw if isinstance(raw, dict) else {}
    pitch = _positive(pinout.get("pitch"), 1.27 if package["type"] == "to92" else 2.54, "pinout.pitch", warnings)
    default_inset = 0.0 if package["type"] in {"dip", "to92"} else 1.27
    rows = []
    for i, row in enumerate(pinout.get("rows") or []):
        if not isinstance(row, dict):
            warnings.append(f"pinout.rows[{i}] ignorée : ce doit être un objet.")
            continue
        side = _text(row.get("side")).lower() or "left"
        if side not in SIDES:
            warnings.append(f"pinout.rows[{i}].side : « {side} » inconnu, « left » utilisé.")
            side = "left"
        inset = _optional_float(row.get("inset"))
        rows.append({
            "name": _text(row.get("name")) or f"R{i + 1}",
            "side": side,
            "pitch": _positive(row.get("pitch"), pitch, f"pinout.rows[{i}].pitch", warnings),
            "inset": default_inset if inset is None else inset,
            "start": _optional_float(row.get("start")),
            "pins": [_normalize_pin(p, j, warnings) for j, p in enumerate(row.get("pins") or [])],
        })
    return {"pitch": pitch, "rows": rows}


def _normalize_components(raw: Any, warnings: list[str]) -> list[dict[str, Any]]:
    components = []
    for i, comp in enumerate(raw or []):
        if not isinstance(comp, dict):
            warnings.append(f"components[{i}] ignoré : ce doit être un objet.")
            continue
        components.append({
            "name": _text(comp.get("name")),
            "x": _optional_float(comp.get("x")) or 0.0,
            "y": _optional_float(comp.get("y")) or 0.0,
            "width": _positive(comp.get("width"), 3, f"components[{i}].width", warnings),
            "length": _positive(comp.get("length"), 3, f"components[{i}].length", warnings),
            "height": _positive(comp.get("height"), 1, f"components[{i}].height", warnings),
            "color": _color(comp.get("color"), "#2a2d34", f"components[{i}].color", warnings),
            "label": _text(comp.get("label")),
            "shape": "cylinder" if _text(comp.get("shape")).lower() == "cylinder" else "box",
        })
    return components


def normalize(meta: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate the front matter and fill in defaults."""
    warnings: list[str] = []
    name = _text(meta.get("name"))
    if not name:
        raise SheetError("Le champ « name » est obligatoire.")
    tags = meta.get("tags") or []
    if not isinstance(tags, list):
        tags = [t.strip() for t in str(tags).split(",")]
    specs = meta.get("specs") or {}
    if not isinstance(specs, dict):
        warnings.append("specs : doit être une liste « clé: valeur ».")
        specs = {}
    links = meta.get("links") or []
    if isinstance(links, dict):
        links = [{"title": k, "url": v} for k, v in links.items()]
    links = [
        {"title": _text(link.get("title")) or _text(link.get("url")), "url": _text(link.get("url"))}
        for link in links if isinstance(link, dict) and _text(link.get("url"))
    ]
    model3d = _text(meta.get("model3d"))
    if model3d and Path(model3d).suffix.lower() not in MODEL_EXTENSIONS:
        warnings.append(f"model3d : format non pris en charge ({', '.join(sorted(MODEL_EXTENSIONS))}).")
        model3d = ""
    package = _normalize_package(meta.get("package"), warnings)
    return {
        "name": name,
        "category": _text(meta.get("category")) or "Divers",
        "manufacturer": _text(meta.get("manufacturer")),
        "part_number": _text(meta.get("part_number")),
        "description": _text(meta.get("description")),
        "tags": [_text(t) for t in tags if _text(t)],
        "specs": {_text(k): _text(v) for k, v in specs.items()},
        "links": links,
        "model3d": model3d,
        "package": package,
        "pinout": _normalize_pinout(meta.get("pinout"), package, warnings),
        "components": _normalize_components(meta.get("components"), warnings),
    }, warnings


def parse(sheet_id: str, source: str) -> Sheet:
    meta, body = split_front_matter(source)
    normalized, warnings = normalize(meta)
    return Sheet(id=sheet_id, meta=normalized, body=body, source=source, warnings=warnings)


def check_id(sheet_id: str) -> str:
    if not ID_RE.fullmatch(sheet_id or ""):
        raise SheetError("Identifiant invalide : lettres minuscules, chiffres et tirets (64 caractères au plus).")
    return sheet_id


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:64] or "sheet"


class SheetLibrary:
    """Access to the sheets directory. Files changed on disk are re-read on each call."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._cache: dict[str, tuple[float, Sheet | SheetError]] = {}

    @property
    def models_dir(self) -> Path:
        return self.directory / "models"

    def path(self, sheet_id: str) -> Path:
        return self.directory / f"{check_id(sheet_id)}.md"

    def _load(self, path: Path) -> Sheet | SheetError:
        sheet_id = path.stem
        mtime = path.stat().st_mtime
        cached = self._cache.get(sheet_id)
        if cached and cached[0] == mtime:
            return cached[1]
        try:
            result: Sheet | SheetError = parse(sheet_id, path.read_text(encoding="utf-8"))
        except SheetError as exc:
            result = exc
        except UnicodeDecodeError as exc:
            result = SheetError(f"Encodage invalide : {exc}")
        self._cache[sheet_id] = (mtime, result)
        return result

    def list(self) -> tuple[list[Sheet], list[dict[str, str]]]:
        sheets, errors = [], []
        if not self.directory.is_dir():
            return sheets, errors
        for path in sorted(self.directory.glob("*.md")):
            if path.name.startswith("_") or not ID_RE.fullmatch(path.stem):
                continue
            result = self._load(path)
            if isinstance(result, Sheet):
                sheets.append(result)
            else:
                errors.append({"id": path.stem, "error": str(result)})
        sheets.sort(key=lambda s: (s.meta["category"].lower(), s.meta["name"].lower()))
        return sheets, errors

    def get(self, sheet_id: str) -> Sheet:
        path = self.path(sheet_id)
        if not path.is_file():
            raise FileNotFoundError(sheet_id)
        result = self._load(path)
        if isinstance(result, SheetError):
            raise result
        return result

    def source(self, sheet_id: str) -> str:
        path = self.path(sheet_id)
        if not path.is_file():
            raise FileNotFoundError(sheet_id)
        return path.read_text(encoding="utf-8")

    def exists(self, sheet_id: str) -> bool:
        return self.path(sheet_id).is_file()

    def write(self, sheet_id: str, source: str) -> Sheet:
        sheet = parse(check_id(sheet_id), source)  # never write an invalid sheet
        self.directory.mkdir(parents=True, exist_ok=True)
        _atomic_write(self.path(sheet_id), source.replace("\r\n", "\n").encode("utf-8"))
        self._cache.pop(sheet_id, None)
        return sheet

    def delete(self, sheet_id: str) -> None:
        path = self.path(sheet_id)
        if not path.is_file():
            raise FileNotFoundError(sheet_id)
        path.unlink()
        self._cache.pop(sheet_id, None)

    def model_path(self, name: str) -> Path:
        """Resolve a 3D model path, refusing anything outside the models/ directory."""
        name = name.removeprefix("models/")
        path = (self.models_dir / name).resolve()
        if self.models_dir.resolve() not in path.parents or path.suffix.lower() not in MODEL_EXTENSIONS:
            raise FileNotFoundError(name)
        return path

    def save_model(self, filename: str, content: bytes) -> str:
        extension = Path(filename).suffix.lower()
        if extension not in MODEL_EXTENSIONS:
            raise SheetError(f"Format non pris en charge ({', '.join(sorted(MODEL_EXTENSIONS))}).")
        stem = slugify(Path(filename).stem)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(self.models_dir / f"{stem}{extension}", content)
        return f"models/{stem}{extension}"


def _atomic_write(path: Path, content: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
