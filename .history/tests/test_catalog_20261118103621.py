from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml
from fastapi.testclient import TestClient

from app.catalog import correction_url, normalize
from app.main import create_app
from app.sheets import SheetLibrary

ROOT = Path(__file__).resolve().parent.parent
FORMS = ROOT / ".github" / "ISSUE_TEMPLATE"
REPOSITORY = "https://github.com/astraeos-dev/Promethee"


def form_field_ids(name: str) -> set[str]:
    form = yaml.safe_load((FORMS / name).read_text(encoding="utf-8"))
    return {field["id"] for field in form["body"] if "id" in field}


def query(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}


def load_catalog() -> list[dict]:
    devices, problems = normalize(yaml.safe_load((ROOT / "sheets" / "catalog.yaml").read_text(encoding="utf-8")))
    assert problems == []
    return devices


def test_catalog_is_valid():
    devices = load_catalog()
    assert len(devices) >= 60
    names = [d["name"].casefold() for d in devices]
    assert len(names) == len(set(names)), "two entries would show the same name in the list"


def test_every_sheet_is_in_the_catalog():
    # Picking the name of a device that has a sheet links the new item to it.
    ids = {d["id"] for d in load_catalog()}
    sheets, errors = SheetLibrary(ROOT / "sheets").list()
    assert errors == []
    assert {s.id for s in sheets} <= ids


def test_correction_url_fills_fields_of_the_form():
    params = query(correction_url(REPOSITORY, "ne555", "NE555"))
    assert params.pop("template") == "correction-fiche.yml"
    assert params.pop("title") == "Correction : NE555"
    # Every other parameter must be a field id of the form, or GitHub ignores it.
    assert set(params) <= form_field_ids("correction-fiche.yml")
    assert params == {"sheet": "ne555"}
    assert "+" not in correction_url(REPOSITORY, "ne555", "Module X")


def test_invalid_entries_are_left_out():
    devices, problems = normalize({"devices": [
        {"id": "ok", "name": "OK", "category": "Capteur", "links": ["https://example.org"]},
        {"id": "ok", "name": "Duplicate", "category": "Capteur"},
        {"id": "Bad Id", "name": "X", "category": "Capteur"},
        {"id": "no-name", "category": "Capteur"},
        {"id": "bad-link", "name": "X", "category": "Capteur", "links": ["ftp://example.org"]},
        "not a mapping",
    ]})
    assert [d["id"] for d in devices] == ["ok"]
    assert len(problems) == 5
    assert normalize(None) == ([], []) and normalize({"devices": None}) == ([], [])


def test_api_links_devices_that_already_have_a_sheet(tmp_path):
    sheets = tmp_path / "sheets"
    sheets.mkdir()
    (sheets / "module-x.md").write_text("---\nname: Module X\n---\n", encoding="utf-8")
    (sheets / "catalog.yaml").write_text(yaml.safe_dump({"devices": [
        {"id": "module-x", "name": "Module X", "category": "Capteur", "package": "Module"},
        {"id": "led-5mm", "name": "LED 5 mm", "category": "LED", "values": ["red", "green"]},
    ]}, allow_unicode=True), encoding="utf-8")
    with TestClient(create_app(sheets, tmp_path / "db.sqlite3")) as client:
        catalog = client.get("/api/catalog").json()
        assert [(d["id"], d["has_sheet"]) for d in catalog["devices"]] == [("module-x", True), ("led-5mm", False)]
        assert catalog["categories"] == ["Capteur", "LED"]
        assert catalog["devices"][1]["values"] == ["red", "green"]
        sheet = client.get("/api/sheets/module-x").json()
        assert query(sheet["correction_url"])["sheet"] == "module-x"


def test_api_catalog_without_file(tmp_path):
    sheets = tmp_path / "sheets"
    sheets.mkdir()
    with TestClient(create_app(sheets, tmp_path / "db.sqlite3")) as client:
        assert client.get("/api/catalog").json() == {"devices": [], "categories": []}
