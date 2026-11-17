import pytest
from fastapi.testclient import TestClient

from app.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "sheets", tmp_path / "inventory.sqlite3")) as c:
        yield c


def test_health_and_ui(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert "Prométhée" in client.get("/").text


def test_sheets_are_read_only(client):
    assert client.get("/api/sheets").json() == {"sheets": [], "errors": []}
    assert client.get("/api/sheets/nothing").status_code == 404
    assert client.post("/api/sheets", json={"source": "---\nname: x\n---\n"}).status_code == 405
    assert client.get("/api/about").json()["repository"].startswith("https://github.com/")


def test_bundled_sheets_and_models_are_served():
    with TestClient(create_app()) as client:
        sheet = client.get("/api/sheets/ne555").json()
        model = sheet["parts"][0]["model"]
        response = client.get(f"/api/{model}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "model/gltf-binary"
        assert response.content[:4] == b"glTF"


def test_inventory_lifecycle(client):
    item = client.post("/api/items", json={"name": "Résistance", "value": "10 kΩ", "quantity": 10, "threshold": 5}).json()
    response = client.post(f"/api/items/{item['id']}/movements", json={"delta": -7, "reason": "Projet"})
    assert response.json()["quantity"] == 3
    assert client.post(f"/api/items/{item['id']}/movements", json={"delta": -4}).status_code == 422
    assert [x["id"] for x in client.get("/api/items?low_stock=true").json()] == [item["id"]]
    assert [x["id"] for x in client.get("/api/alerts").json()] == [item["id"]]
    assert client.put(f"/api/items/{item['id']}", json={"quantity": 20}).json()["quantity"] == 20
    assert len(client.get(f"/api/items/{item['id']}/movements").json()) == 3
    assert client.post("/api/items", json={"name": ""}).status_code == 422
    assert client.post("/api/items", json={"name": "x", "quantity": -1}).status_code == 422


def test_csv_export_import(client):
    client.post("/api/items", json={"name": "LED rouge", "quantity": 12})
    exported = client.get("/api/export.csv").content
    result = client.post("/api/import", files={"file": ("s.csv", exported, "text/csv")}).json()
    assert result == {"created": 0, "updated": 1}
    # French headers from a hand-made spreadsheet are accepted too.
    french = "nom;quantité;emplacement\nLED verte;5;Tiroir D1\n".encode()
    assert client.post("/api/import", files={"file": ("n.csv", french)}).json()["created"] == 1
    items = client.get("/api/items").json()
    assert {i["name"]: i["location"] for i in items} == {"LED rouge": "", "LED verte": "Tiroir D1"}
