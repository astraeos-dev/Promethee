import pytest
from fastapi.testclient import TestClient

from app.main import creer_app

FICHE = "---\nnom: Capteur essai\ncategorie: Capteur\n---\nTexte.\n"


@pytest.fixture
def client(tmp_path):
    with TestClient(creer_app(tmp_path / "fiches", tmp_path / "stock.sqlite3")) as c:
        yield c


def test_sante_et_interface(client):
    assert client.get("/api/sante").json()["statut"] == "ok"
    assert "Prométhée" in client.get("/").text


def test_cycle_fiche(client):
    r = client.post("/api/fiches", json={"source": FICHE})
    assert r.status_code == 201 and r.json()["id"] == "capteur-essai"
    assert client.post("/api/fiches", json={"source": FICHE}).status_code == 409
    assert client.get("/api/fiches/capteur-essai").json()["categorie"] == "Capteur"
    assert client.put("/api/fiches/capteur-essai", json={"source": "invalide"}).status_code == 422
    assert client.post("/api/fiches/apercu", json={"source": FICHE}).json()["nom"] == "Capteur essai"
    assert client.delete("/api/fiches/capteur-essai").status_code == 204
    assert client.get("/api/fiches/capteur-essai").status_code == 404


def test_cycle_stock(client):
    a = client.post("/api/articles", json={"nom": "Résistance", "valeur": "10 kΩ", "quantite": 10, "seuil": 5}).json()
    r = client.post(f"/api/articles/{a['id']}/mouvements", json={"delta": -7, "motif": "Projet"})
    assert r.json()["quantite"] == 3
    assert client.post(f"/api/articles/{a['id']}/mouvements", json={"delta": -4}).status_code == 422
    assert [x["id"] for x in client.get("/api/articles?alerte=true").json()] == [a["id"]]
    assert client.put(f"/api/articles/{a['id']}", json={"quantite": 20}).json()["quantite"] == 20
    assert len(client.get(f"/api/articles/{a['id']}/mouvements").json()) == 3
    assert client.post("/api/articles", json={"nom": ""}).status_code == 422
    assert client.post("/api/articles", json={"nom": "x", "quantite": -1}).status_code == 422


def test_export_import_csv(client):
    client.post("/api/articles", json={"nom": "LED rouge", "quantite": 12})
    csv = client.get("/api/export.csv").content
    r = client.post("/api/import", files={"fichier": ("s.csv", csv, "text/csv")}).json()
    assert r == {"crees": 0, "mis_a_jour": 1}
    nouveau = "nom;quantite;emplacement\nLED verte;5;Tiroir D1\n".encode()
    assert client.post("/api/import", files={"fichier": ("n.csv", nouveau)}).json()["crees"] == 1
    assert len(client.get("/api/articles").json()) == 2
