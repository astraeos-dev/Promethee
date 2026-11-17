"""The model builder (tools/build_models.py) needs the dev dependencies."""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("trimesh")
pytest.importorskip("shapely")

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("build_models", ROOT / "tools" / "build_models.py")
build_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_models)

from app.sheets import parse  # noqa: E402


def build(sheet_id):
    sheet = parse(sheet_id, (ROOT / "sheets" / f"{sheet_id}.md").read_text(encoding="utf-8"))
    return sheet, build_models.build_device(sheet, build_models.load_manifest())


def test_board_matches_the_sheet():
    sheet, scene = build("bme280-module")
    package = sheet.meta["package"]
    (min_x, min_y, min_z), (max_x, max_y, max_z) = scene.bounds
    # The board is centred and its lower face is at Y = 0; parts may overhang slightly.
    assert max_x - min_x == pytest.approx(package["width"], abs=0.5)
    assert max_z - min_z >= package["length"]
    assert min_y < 0 < package["thickness"] < max_y
    names = {mesh.visual.material.name for mesh in scene.geometry.values()}
    assert {"fr4", "tin", "solder", "plastic"} <= names


def test_material_colours_are_linear():
    material = build_models.pbr((24, 24, 26))
    assert tuple(material.baseColorFactor[:3]) == (2, 2, 3)  # sRGB 24 is about 0.009 in linear light


def test_loose_transistor_gets_full_length_leads():
    _, scene = build("pn2222a")
    (_, min_y, _), _ = scene.bounds
    assert min_y < -12
