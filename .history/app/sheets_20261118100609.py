"""Device sheets: one Markdown file with a YAML front matter per device.

Sheets ship with the application (sheets/ directory) and are read-only at
runtime; new sheets are requested through GitHub issues and added in
releases. Each sheet comes with a complete 3D model of the device,
sheets/models/<id>.glb, built from the sheet by tools/build_models.py.

The format is described in docs/sheet-format.md. Files whose name starts
with "_" (such as the blank template) are not listed. Messages returned to
the user (errors, warnings) are in French, like the UI.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import markdown
import yaml

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
PART_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(.*)\Z", re.S)
COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")

PIN_TYPES = {
    "power", "ground", "gpio", "analog", "pwm", "i2c", "spi", "uart",
    "control", "reserved", "nc", "other",
}
PACKAGE_TYPES = {"board", "module", "dip", "to92"}
BOARD_TYPES = {"board", "module"}
ROW_SIDES = {"left", "right", "top", "bottom"}
BOARD_SIDES = {"top", "bottom"}
SHAPES = {"box", "cylinder"}
FINISHES = {"gold", "tin"}

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
            "has_model": bool(m.get("model")),
        }

    def full(self) -> dict[str, Any]:
        html = markdown.markdown(
            self.body,
            extensions=["tables", "fenced_code", "sane_lists", "toc", "attr_list"],
            output_format="html",
        )
        return {**self.meta, "id": self.id, "html": html, "warnings": self.warnings}


# ---------- Value helpers ----------

def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _positive(value: Any, default: float, key: str, warnings: list[str]) -> float:
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        warnings.append(f"{key} : « {value} » is not a number, {default} used.")
        return default
    if number <= 0:
        warnings.append(f"{key} : must be positive, {default} used.")
        return default
    return number


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return default if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None


def _color(value: Any, default: str, key: str, warnings: list[str]) -> str:
    color = _text(value) or default
    if not COLOR_RE.fullmatch(color):
        warnings.append(f"{key} : « {color} » must be written as #rrggbb.")
        return default
    return color


def _choice(value: Any, allowed: set[str], default: str, key: str, warnings: list[str]) -> str:
    choice = _text(value).lower() or default
    if choice not in allowed:
        warnings.append(f"{key} : « {choice} » unknown (expected : {', '.join(sorted(allowed))}), « {default} » used.")
        return default
    return choice


def _objects(raw: Any, key: str, warnings: list[str]) -> list[tuple[int, dict]]:
    items = []
    for i, item in enumerate(raw or []):
        if isinstance(item, dict):
            items.append((i, item))
        else:
            warnings.append(f"{key}[{i}] ignored : this must be an object.")
    return items


# ---------- Normalization ----------

def split_front_matter(source: str) -> tuple[dict[str, Any], str]:
    """Split the YAML front matter from the Markdown body."""
    source = source.lstrip("﻿")
    match = FRONT_MATTER_RE.match(source)
    if not match:
        raise SheetError("The YAML front matter is missing : the sheet must start with a line « --- ».")
    try:
        meta = yaml.load(match.group(1), Loader=_Loader) or {}
    except yaml.YAMLError as exc:
        raise SheetError(f"Invalid YAML front matter : {exc}") from exc
    if not isinstance(meta, dict):
        raise SheetError("The YAML front matter must be a list of key-value pairs.")
    return meta, match.group(2)


def _normalize_package(raw: Any, warnings: list[str]) -> dict[str, Any]:
    pkg = raw if isinstance(raw, dict) else {}
    kind = _choice(pkg.get("type"), PACKAGE_TYPES, "board", "package.type", warnings)
    length, width, thickness, color = PACKAGE_DEFAULTS[kind]
    width = _positive(pkg.get("width"), width, "package.width", warnings)
    length = _positive(pkg.get("length"), length, "package.length", warnings)
    package = {
        "type": kind,
        "length": length,
        "width": width,
        "thickness": _positive(pkg.get("thickness"), thickness, "package.thickness", warnings),
        "color": _color(pkg.get("color"), color, "package.color", warnings),
        "marking": _text(pkg.get("marking")),
        # Printed circuit board details, used by the 3D model.
        "finish": _choice(pkg.get("finish"), FINISHES, "gold", "package.finish", warnings),
        "corner_radius": min(_number(pkg.get("corner_radius"), 0.6), width / 2, length / 2),
        "silkscreen_color": _color(pkg.get("silkscreen_color"), "#f1f3f6", "package.silkscreen_color", warnings),
        "silkscreen": [],
        "holes": [],
    }
    for i, item in _objects(pkg.get("silkscreen"), "package.silkscreen", warnings):
        if not _text(item.get("text")):
            continue
        package["silkscreen"].append({
            "text": _text(item.get("text")),
            "x": _number(item.get("x")),
            "y": _number(item.get("y")),
            "size": _positive(item.get("size"), 1.0, f"package.silkscreen[{i}].size", warnings),
            "rotation": _number(item.get("rotation")),
            "side": _choice(item.get("side"), BOARD_SIDES, "top", f"package.silkscreen[{i}].side", warnings),
        })
    for i, item in _objects(pkg.get("holes"), "package.holes", warnings):
        drill = _positive(item.get("drill"), 1.0, f"package.holes[{i}].drill", warnings)
        package["holes"].append({
            "x": _number(item.get("x")),
            "y": _number(item.get("y")),
            "drill": drill,
            "pad": max(_number(item.get("pad")), 0.0),  # 0: not plated
            "square": bool(item.get("square")),
        })
    return package


def _normalize_pin(raw: Any, index: int, warnings: list[str]) -> dict[str, Any]:
    pin = raw if isinstance(raw, dict) else {"name": raw}
    name = _text(pin.get("name")) or "?"
    functions = pin.get("functions") or []
    if not isinstance(functions, list):
        functions = [functions]
    return {
        "n": _text(pin.get("n")) or str(index + 1),
        "name": name,
        # Text printed next to the pin on the real board, when it differs from the name.
        "silkscreen": _text(pin.get("silkscreen")) or name,
        "type": _choice(pin.get("type"), PIN_TYPES, "other", f"Pin « {name} » : type", warnings),
        "functions": [_text(f) for f in functions if _text(f)],
        "description": _text(pin.get("description")),
    }


def _normalize_pinout(raw: Any, package: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    pinout = raw if isinstance(raw, dict) else {}
    pitch = _positive(pinout.get("pitch"), 1.27 if package["type"] == "to92" else 2.54, "pinout.pitch", warnings)
    default_inset = 0.0 if package["type"] in {"dip", "to92"} else 1.27
    rows = []
    for i, row in _objects(pinout.get("rows"), "pinout.rows", warnings):
        inset = _optional_float(row.get("inset"))
        rows.append({
            "name": _text(row.get("name")) or f"R{i + 1}",
            "side": _choice(row.get("side"), ROW_SIDES, "left", f"pinout.rows[{i}].side", warnings),
            "pitch": _positive(row.get("pitch"), pitch, f"pinout.rows[{i}].pitch", warnings),
            "inset": default_inset if inset is None else inset,
            "start": _optional_float(row.get("start")),
            "pins": [_normalize_pin(p, j, warnings) for j, p in enumerate(row.get("pins") or [])],
        })
    _place_pins(package, rows)
    return {"pitch": pitch, "rows": rows}


def _place_pins(package: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    """Give each pin its position (x, y in mm, seen from above, from the top left corner).

    Pins of a row are listed in physical order: top to bottom on the left and
    right sides, left to right on the top and bottom sides. A row is centred
    on its side unless "start" gives the position of its first pin.
    """
    for row in rows:
        count = len(row["pins"])
        vertical = row["side"] in {"left", "right"}
        side_length = package["length"] if vertical else package["width"]
        start = row["start"] if row["start"] is not None else (side_length - (count - 1) * row["pitch"]) / 2
        for i, pin in enumerate(row["pins"]):
            along = start + i * row["pitch"]
            x, y = {
                "left": (row["inset"], along),
                "right": (package["width"] - row["inset"], along),
                "top": (along, row["inset"]),
                "bottom": (along, package["length"] - row["inset"]),
            }[row["side"]]
            pin["x"], pin["y"] = round(x, 4), round(y, 4)


def _normalize_parts(raw: Any, warnings: list[str]) -> list[dict[str, Any]]:
    """Parts of the 3D model: a converted KiCad model ("model") or a simple shape ("shape")."""
    parts = []
    for i, part in _objects(raw, "parts", warnings):
        key = f"parts[{i}]"
        model = _text(part.get("model"))
        shape = _text(part.get("shape")).lower()
        if model and not PART_NAME_RE.fullmatch(model):
            warnings.append(f"{key}.model : « {model} » is not a part name (see tools/parts.yaml).")
            continue
        if not model and shape not in SHAPES:
            warnings.append(f"{key} ignored : indicate « model » or « shape » (box or cylinder).")
            continue
        parts.append({
            "name": _text(part.get("name")),
            "model": model,
            "shape": "" if model else shape,
            "width": _positive(part.get("width"), 1.0, f"{key}.width", warnings),
            "length": _positive(part.get("length"), 1.0, f"{key}.length", warnings),
            "height": _positive(part.get("height"), 1.0, f"{key}.height", warnings),
            "x": _number(part.get("x")),
            "y": _number(part.get("y")),
            "z": _number(part.get("z")),
            "rotation": _number(part.get("rotation")),
            "side": _choice(part.get("side"), BOARD_SIDES, "top", f"{key}.side", warnings),
            "color": _color(part.get("color"), "#2a2d34", f"{key}.color", warnings),
            "label": _text(part.get("label")),
        })
    return parts


def normalize(meta: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate the front matter and fill in defaults."""
    warnings: list[str] = []
    name = _text(meta.get("name"))
    if not name:
        raise SheetError("The « name » field is required.")
    tags = meta.get("tags") or []
    if not isinstance(tags, list):
        tags = [t.strip() for t in str(tags).split(",")]
    specs = meta.get("specs") or {}
    if not isinstance(specs, dict):
        warnings.append("specs : must be a list of key-value pairs.")
        specs = {}
    links = meta.get("links") or []
    if isinstance(links, dict):
        links = [{"title": k, "url": v} for k, v in links.items()]
    links = [
        {"title": _text(link.get("title")) or _text(link.get("url")), "url": _text(link.get("url"))}
        for link in links if isinstance(link, dict) and _text(link.get("url"))
    ]
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
        "package": package,
        "pinout": _normalize_pinout(meta.get("pinout"), package, warnings),
        "parts": _normalize_parts(meta.get("parts"), warnings),
    }, warnings


def parse(sheet_id: str, source: str) -> Sheet:
    meta, body = split_front_matter(source)
    normalized, warnings = normalize(meta)
    return Sheet(id=sheet_id, meta=normalized, body=body, source=source, warnings=warnings)


def model_inputs_hash(meta: dict[str, Any]) -> str:
    """Fingerprint of what the 3D model is built from, to detect a stale model."""
    parts = [{k: v for k, v in part.items() if k != "size"} for part in meta["parts"]]
    inputs = {"package": meta["package"], "pinout": meta["pinout"], "parts": parts}
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]


def check_id(sheet_id: str) -> str:
    if not ID_RE.fullmatch(sheet_id or ""):
        raise SheetError("Invalid identifier : lowercase letters, numbers and hyphens (up to 64 characters).")
    return sheet_id


class SheetLibrary:
    """Read-only access to the sheets directory, re-read when files change."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._cache: dict[str, tuple[float, Sheet | SheetError]] = {}

    @property
    def models_dir(self) -> Path:
        return self.directory / "models"

    def part_sizes(self) -> dict[str, list[float]]:
        """Size (x, height, z in mm) of each converted part, written by tools/build_models.py."""
        try:
            return json.loads((self.models_dir / "parts.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

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
            result = SheetError(f"Invalid encoding : {exc}")
        if isinstance(result, Sheet):
            self._attach_model(result)
        self._cache[sheet_id] = (mtime, result)
        return result

    def _attach_model(self, sheet: Sheet) -> None:
        model = self.models_dir / f"{sheet.id}.glb"
        sheet.meta["model"] = f"models/{sheet.id}.glb" if model.is_file() else ""
        sizes = self.part_sizes()
        for part in sheet.meta["parts"]:
            if part["model"]:
                part["size"] = sizes.get(part["model"])
            else:
                part["size"] = [part["width"], part["height"], part["length"]]

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

    def model_path(self, name: str) -> Path:
        """Resolve a device model path, refusing anything outside the models/ directory."""
        name = name.removeprefix("models/")
        path = (self.models_dir / name).resolve()
        if self.models_dir.resolve() not in path.parents or path.suffix.lower() != ".glb":
            raise FileNotFoundError(name)
        return path
