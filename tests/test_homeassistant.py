import json

from fastapi.testclient import TestClient

from app.homeassistant import Publieur, configuration, etats
from app.main import creer_app


def test_configuration(monkeypatch):
    for v in ("SUPERVISOR_TOKEN", "PROMETHEE_HA_URL", "PROMETHEE_HA_TOKEN", "PROMETHEE_HA"):
        monkeypatch.delenv(v, raising=False)
    assert configuration() is None
    monkeypatch.setenv("PROMETHEE_HA_URL", "http://ha.local:8123/")
    monkeypatch.setenv("PROMETHEE_HA_TOKEN", "abc")
    assert configuration() == ("http://ha.local:8123/api", "abc")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "sup")
    assert configuration() == ("http://supervisor/core/api", "sup")
    monkeypatch.setenv("PROMETHEE_HA", "off")
    assert configuration() is None


def test_etats():
    alerte = {"nom": "NE555", "valeur": "", "quantite": 1, "seuil": 5, "emplacement": "C2", "id": 3}
    e = etats({"articles": 4, "pieces": 20, "alertes": 1, "fiches": 5}, [alerte])
    assert e["sensor.promethee_alertes"]["state"] == 1
    assert e["sensor.promethee_alertes"]["attributes"]["articles"] == [
        {"nom": "NE555", "valeur": "", "quantite": 1, "seuil": 5, "emplacement": "C2"}]
    assert e["sensor.promethee_pieces"]["attributes"]["unit_of_measurement"] == "pièces"


def test_publication(monkeypatch, tmp_path):
    envois = []

    class Reponse:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def faux_urlopen(requete, timeout):
        envois.append((requete.full_url, requete.headers["Authorization"], json.loads(requete.data)))
        return Reponse()

    monkeypatch.setattr("urllib.request.urlopen", faux_urlopen)
    p = Publieur(lambda: {"sensor.x": {"state": 1, "attributes": {}}}, ("http://supervisor/core/api", "jeton"))
    p.publier()
    assert envois == [("http://supervisor/core/api/states/sensor.x", "Bearer jeton", {"state": 1, "attributes": {}})]


def test_modification_signale(tmp_path):
    p = Publieur(lambda: {}, None)
    with TestClient(creer_app(tmp_path / "f", tmp_path / "s.db", publieur=p)) as c:
        c.post("/api/fiches/apercu", json={"source": "---\nnom: x\n---\n"})
        assert not p._evenement.is_set()
        c.post("/api/articles", json={"nom": "LED"})
        assert p._evenement.is_set()


def test_prefixe_ingress(tmp_path):
    with TestClient(creer_app(tmp_path / "f", tmp_path / "s.db")) as c:
        assert '<base href="/">' in c.get("/").text
        page = c.get("/", headers={"X-Ingress-Path": "/api/hassio_ingress/AbC-12_x"}).text
        assert '<base href="/api/hassio_ingress/AbC-12_x/">' in page
        assert '<base href="/">' in c.get("/", headers={"X-Ingress-Path": '/"><script>'}).text
        assert c.get("/api/alertes").json() == []


def test_version_module_coherente():
    import re
    from pathlib import Path

    from app import __version__
    config = (Path(__file__).resolve().parent.parent / "promethee" / "config.yaml").read_text(encoding="utf-8")
    assert re.search(r'^version: "(.+)"$', config, re.M)[1] == __version__
