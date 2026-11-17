import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import __version__
from app.home_assistant import Publisher, sensor_states, settings
from app.main import create_app

ROOT = Path(__file__).resolve().parent.parent


def test_settings(monkeypatch):
    for name in ("SUPERVISOR_TOKEN", "PROMETHEE_HA_URL", "PROMETHEE_HA_TOKEN", "PROMETHEE_HA"):
        monkeypatch.delenv(name, raising=False)
    assert settings() is None
    monkeypatch.setenv("PROMETHEE_HA_URL", "http://ha.local:8123/")
    monkeypatch.setenv("PROMETHEE_HA_TOKEN", "abc")
    assert settings() == ("http://ha.local:8123/api", "abc")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "sup")
    assert settings() == ("http://supervisor/core/api", "sup")
    monkeypatch.setenv("PROMETHEE_HA", "off")
    assert settings() is None


def test_sensor_states():
    low = {"id": 3, "name": "NE555", "value": "", "quantity": 1, "threshold": 5, "location": "C2"}
    states = sensor_states({"items": 4, "parts": 20, "low_stock": 1, "sheets": 5}, [low])
    assert states["sensor.promethee_low_stock"]["state"] == 1
    assert states["sensor.promethee_low_stock"]["attributes"]["items"] == [
        {"name": "NE555", "value": "", "quantity": 1, "threshold": 5, "location": "C2"}]
    assert states["sensor.promethee_parts"]["attributes"]["unit_of_measurement"] == "pièces"


def test_publish_posts_each_state(monkeypatch):
    sent = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        sent.append((request.full_url, request.headers["Authorization"], json.loads(request.data)))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    publisher = Publisher(lambda: {"sensor.x": {"state": 1, "attributes": {}}}, ("http://supervisor/core/api", "token"))
    publisher.publish()
    assert sent == [("http://supervisor/core/api/states/sensor.x", "Bearer token", {"state": 1, "attributes": {}})]


def test_changes_trigger_publication(tmp_path):
    publisher = Publisher(lambda: {}, None)
    with TestClient(create_app(tmp_path / "s", tmp_path / "db.sqlite3", publisher=publisher)) as client:
        client.get("/api/items")
        assert not publisher._changed.is_set()
        client.post("/api/items", json={"name": "LED"})
        assert publisher._changed.is_set()


def test_ingress_prefix(tmp_path):
    with TestClient(create_app(tmp_path / "s", tmp_path / "db.sqlite3")) as client:
        assert '<base href="/">' in client.get("/").text
        page = client.get("/", headers={"X-Ingress-Path": "/api/hassio_ingress/AbC-12_x"}).text
        assert '<base href="/api/hassio_ingress/AbC-12_x/">' in page
        assert '<base href="/">' in client.get("/", headers={"X-Ingress-Path": '/"><script>'}).text


def test_addon_version_matches_app():
    addon = (ROOT / "homeassistant-addon" / "config.yaml").read_text(encoding="utf-8")
    assert re.search(r'^version: "(.+)"$', addon, re.M)[1] == __version__
