from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml
from fastapi.testclient import TestClient

from app.catalog import correction_url, normalize, request_url
from app.main import create_app

ROOT = Path(__file__).resolve().parent.parent
FORMS = ROOT / ".github" / "ISSUE_TEMPLATE"
REPOSITORY = "https://github.com/astraeos-dev/Promethee"


def form_field_ids(name: str) -> set[str]:
    form = yaml.safe_load((FORMS / name).read_text(encoding="utf-8"))
    return {field["id"] for field in form["body"] if "id" in field}


def query(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}


def test_catalog_is_valid():
    devices, problems = normalize(yaml.safe_load((ROOT / "sheets" / "catalog.yaml").read_text(encoding="utf-8")))
    assert problems == []
    assert len(devices) >= 40
    for device in devices:
        assert device["links"], f"{device['id']}: a datasheet or documentation link is needed"


def test_request_url_fills_fields_of_the_form():
    device = {"id": "x", "name": "Module X", "category": "Capteur", "manufacturer": "ACME",
              "part_number": "X-1", "description": "", "dimensions": "10 × 20 mm",
              "links": ["https://example.org/a.pdf", "https://example.org/b"]}
    params = query(request_url(REPOSITORY, device))
    assert params.pop("template") == "fiche.yml" and (FORMS / "fiche.yml").is_file()
    assert params.pop("title") == "Fiche : Module X"
    # Every other parameter must be a field id of the form, or GitHub ignores it.
    assert set(params) <= form_field_ids("fiche.yml")
    assert params == {"device": "Module X", "part_number": "ACME X-1", "category": "Capteur",
                      "links": "https://example.org/a.pdf\nhttps://example.org/b", "dimensions": "10 × 20 mm"}
    assert "%20" in request_url(REPOSITORY, device) and "+" not in request_url(REPOSITORY, device)
    assert query(request_url(REPOSITORY)) == {"template": "fiche.yml", "title": "Fiche : "}


def test_correction_url_fills_fields_of_the_form():
    params = query(correction_url(REPOSITORY, "ne555", "NE555"))
    assert params.pop("template") == "correction-fiche.yml"
    assert params.pop("title") == "Correction : NE555"
    assert set(params) <= form_field_ids("correction-fiche.yml")


def test_invalid_entries_are_left_out():
    devices, problems = normalize({"devices": [
        {"id": "ok", "name": "OK", "category": "Capteur", "links": ["https://example.org"]},
        {"id": "ok", "name": "Duplicate", "category": "Capteur"},
        {"id": "Bad Id", "name": "X", "category": "Capteur"},
        {"id": "no-name", "category": "Capteur"},
        {"id": "bad-link", "name": "X", "category": "Capteur", "links": ["ftp://example.org"]},
    ]})
    assert [d["id"] for d in devices] == ["ok"]
    assert len(problems) == 4


def test_api_links_devices_that_already_have_a_sheet(tmp_path):
    sheets = tmp_path / "sheets"
    sheets.mkdir()
    (sheets / "module-x.md").write_text("---\nname: Module X\n---\n", encoding="utf-8")
    (sheets / "catalog.yaml").write_text(yaml.safe_dump({"devices": [
        {"id": "module-x", "name": "Module X", "category": "Capteur", "links": ["https://example.org/x"]},
        {"id": "module-y", "name": "Module Y", "category": "Afficheur", "links": ["https://example.org/y"]},
    ]}, allow_unicode=True), encoding="utf-8")
    with TestClient(create_app(sheets, tmp_path / "db.sqlite3")) as client:
        catalog = client.get("/api/catalog").json()
        assert [(d["id"], d["has_sheet"]) for d in catalog["devices"]] == [("module-x", True), ("module-y", False)]
        assert catalog["categories"] == ["Capteur", "Afficheur"]
        assert query(catalog["devices"][1]["request_url"])["device"] == "Module Y"
        assert query(catalog["other_request_url"])["template"] == "fiche.yml"
        sheet = client.get("/api/sheets/module-x").json()
        assert query(sheet["correction_url"])["sheet"] == "module-x"
