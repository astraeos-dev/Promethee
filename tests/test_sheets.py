from pathlib import Path

import pytest

from app.sheets import SheetError, SheetLibrary, parse

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
  - { model: models/dip-8.glb, x: 1, y: 2, side: bottom, rotation: 90 }
  - { model: ../secret.glb }
  - { model: models/board.stl }
  - { model: models/x.glb, side: inside }
---
""")
    parts = sheet.meta["parts"]
    assert [(p["model"], p["side"]) for p in parts] == [("models/dip-8.glb", "bottom"), ("models/x.glb", "top")]
    assert parts[0]["rotation"] == 90
    assert len(sheet.warnings) == 3


def test_example_parts_have_models_and_sizes():
    sheets, _ = SheetLibrary(SHEETS_DIR).list()
    for sheet in sheets:
        assert sheet.meta["parts"], sheet.id
        for part in sheet.meta["parts"]:
            assert part["size"] and len(part["size"]) == 3, (sheet.id, part["model"])


def test_missing_model_is_reported(tmp_path):
    (tmp_path / "x.md").write_text("---\nname: X\nparts:\n  - { model: models/none.glb }\n---\n")
    sheet = SheetLibrary(tmp_path).get("x")
    assert any("introuvable" in w for w in sheet.warnings)


def test_ids_and_model_paths_are_confined(tmp_path):
    library = SheetLibrary(tmp_path)
    with pytest.raises(SheetError):
        library.path("../etc")
    with pytest.raises(FileNotFoundError):
        library.model_path("../../secret.glb")
    with pytest.raises(FileNotFoundError):
        library.model_path("models/model.stl")
