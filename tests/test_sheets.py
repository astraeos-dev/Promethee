from pathlib import Path

import pytest

from app.sheets import SheetError, SheetLibrary, parse, slugify

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


def test_write_read_delete(tmp_path):
    library = SheetLibrary(tmp_path)
    library.write("sample", MINIMAL)
    assert library.get("sample").meta["name"] == "Test"
    with pytest.raises(SheetError):
        library.write("sample", "invalid")
    assert library.source("sample") == MINIMAL
    library.delete("sample")
    assert not library.exists("sample")


def test_ids_and_model_paths_are_confined(tmp_path):
    library = SheetLibrary(tmp_path)
    with pytest.raises(SheetError):
        library.path("../etc")
    with pytest.raises(FileNotFoundError):
        library.model_path("../../secret.glb")
    assert library.save_model("Mon Modèle.STL", b"solid") == "models/mon-modele.stl"
    assert slugify("Module BME280 (I²C)") == "module-bme280-i2c"
