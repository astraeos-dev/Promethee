import json
from pathlib import Path

import pytest

from app.sheets import SheetError, SheetLibrary, model_inputs_hash, parse

SHEETS_DIR = Path(__file__).resolve().parent.parent / "sheets"

MINIMAL = """---
name: Test
pinout:
  rows:
    - side: top
      pins:
        - { name: ON, type: gpio }
        - { name: NO, type: unknown }
---
Body **bold**.
"""


def test_example_sheets_are_valid():
    sheets, errors = SheetLibrary(SHEETS_DIR).list()
    assert errors == []
    assert len(sheets) >= 5
    for sheet in sheets:
        assert sheet.warnings == [], (sheet.id, sheet.warnings)


def test_template_is_valid():
    sheet = parse("template", (SHEETS_DIR / "_template.md").read_text(encoding="utf-8"))
    assert sheet.warnings == []


def test_yaml_names_stay_strings_and_unknown_type_falls_back():
    sheet = parse("test", MINIMAL)
    pins = sheet.meta["pinout"]["rows"][0]["pins"]
    assert [p["name"] for p in pins] == ["ON", "NO"]
    assert pins[1]["type"] == "other"
    assert any("inconnu" in w for w in sheet.warnings)
    assert "<strong>bold</strong>" in sheet.full()["html"]


@pytest.mark.parametrize("source", ["no front matter", "---\nname: [\n---\n", "---\ndescription: x\n---\n"])
def test_invalid_sheets_are_rejected(source):
    with pytest.raises(SheetError):
        parse("x", source)


def test_parts_are_validated():
    sheet = parse("t", """---
name: T
parts:
  - { model: dip-8, x: 1, y: 2, side: bottom, rotation: 90 }
  - { model: ../secret }
  - { shape: box, width: 3, length: 4, height: 1.5, color: "#d9dbe0" }
  - { shape: sphere }
  - { model: usb-micro-b, side: inside }
---
""")
    parts = sheet.meta["parts"]
    assert [(p["model"], p["shape"], p["side"]) for p in parts] == [
        ("dip-8", "", "bottom"), ("", "box", "top"), ("usb-micro-b", "", "top")]
    assert parts[0]["rotation"] == 90
    assert len(sheet.warnings) == 3


def test_pins_get_their_position():
    sheet = parse("t", """---
name: T
package: { type: board, width: 20, length: 30 }
pinout:
  rows:
    - { side: left, start: 5, pins: [A, B] }
    - { side: bottom, inset: 2, pins: [C, D, E] }
---
""")
    left, bottom = sheet.meta["pinout"]["rows"]
    assert [(p["x"], p["y"]) for p in left["pins"]] == [(1.27, 5), (1.27, 7.54)]
    assert [(p["x"], p["y"]) for p in bottom["pins"]] == [(7.46, 28), (10, 28), (12.54, 28)]
    assert left["pins"][0]["silkscreen"] == "A"


def test_every_sheet_has_an_up_to_date_model():
    index = json.loads((SHEETS_DIR / "models" / "index.json").read_text(encoding="utf-8"))
    sheets, _ = SheetLibrary(SHEETS_DIR).list()
    for sheet in sheets:
        assert sheet.meta["model"] == f"models/{sheet.id}.glb", sheet.id
        assert (SHEETS_DIR / sheet.meta["model"]).read_bytes()[:4] == b"glTF"
        # The model is built from the sheet: run tools/build_models.py after changing it.
        assert index[sheet.id]["inputs"] == model_inputs_hash(parse(sheet.id, sheet.source).meta), sheet.id
        for part in sheet.meta["parts"]:
            assert part["size"] and len(part["size"]) == 3, (sheet.id, part)


def test_ids_and_model_paths_are_confined(tmp_path):
    library = SheetLibrary(tmp_path)
    with pytest.raises(SheetError):
        library.path("../etc")
    with pytest.raises(FileNotFoundError):
        library.model_path("../../secret.glb")
    with pytest.raises(FileNotFoundError):
        library.model_path("models/model.stl")
    assert library.model_path("models/x.glb") == (tmp_path / "models" / "x.glb").resolve()
