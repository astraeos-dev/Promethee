"""Publish the inventory state to Home Assistant as sensors.

Two modes:
- add-on: the Supervisor provides SUPERVISOR_TOKEN and the Home Assistant API
  is reached through http://supervisor/core;
- standalone container: PROMETHEE_HA_URL (e.g. http://192.168.1.10:8123) and
  PROMETHEE_HA_TOKEN (long-lived access token).

Sensors are rewritten after every inventory change and every five minutes,
because Home Assistant forgets these states when it restarts.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
from typing import Any, Callable

log = logging.getLogger("promethee.home_assistant")

REFRESH_SECONDS = 300
MAX_ITEMS_IN_ATTRIBUTE = 50
DISABLED_VALUES = {"0", "no", "false", "off"}


def settings() -> tuple[str, str] | None:
    """Return (API base URL, token), or None when the integration is disabled."""
    if os.environ.get("PROMETHEE_HA", "").lower() in DISABLED_VALUES:
        return None
    token = os.environ.get("SUPERVISOR_TOKEN")
    if token:
        return "http://supervisor/core/api", token
    url, token = os.environ.get("PROMETHEE_HA_URL"), os.environ.get("PROMETHEE_HA_TOKEN")
    if url and token:
        return url.rstrip("/") + "/api", token
    return None


def sensor_states(summary: dict[str, Any], low_stock: list[dict[str, Any]]) -> dict[str, dict]:
    """Build sensor states from the inventory. Display names are in French."""
    common = {"attribution": "Prométhée"}
    return {
        "sensor.promethee_items": {
            "state": summary["items"],
            "attributes": {**common, "friendly_name": "Prométhée references", "icon": "mdi:archive-outline",
                           "unit_of_measurement": "references", "state_class": "measurement"},
        },
        "sensor.promethee_parts": {
            "state": summary["parts"],
            "attributes": {**common, "friendly_name": "Prométhée parts in stock", "icon": "mdi:chip",
                           "unit_of_measurement": "parts", "state_class": "measurement"},
        },
        "sensor.promethee_low_stock": {
            "state": summary["low_stock"],
            "attributes": {
                **common,
                "friendly_name": "Prométhée low stock",
                "icon": "mdi:alert-circle-outline" if summary["low_stock"] else "mdi:check-circle-outline",
                "unit_of_measurement": "items",
                "state_class": "measurement",
                "items": [
                    {k: item[k] for k in ("name", "value", "quantity", "threshold", "location")}
                    for item in low_stock[:MAX_ITEMS_IN_ATTRIBUTE]
                ],
            },
        },
        "sensor.promethee_sheets": {
            "state": summary["sheets"],
            "attributes": {**common, "friendly_name": "Prométhée technical sheets", "icon": "mdi:book-open-variant",
                           "unit_of_measurement": "sheets"},
        },
    }


class Publisher:
    """Background thread pushing sensors without blocking requests."""

    def __init__(self, source: Callable[[], dict[str, dict]], config: tuple[str, str] | None = None):
        self.source = source
        self.config = config if config is not None else settings()
        self._changed = threading.Event()
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None
        self._failing = False

    @property
    def enabled(self) -> bool:
        return self.config is not None

    def start(self) -> None:
        if not self.enabled or self._thread:
            return
        self._thread = threading.Thread(target=self._run, name="promethee-ha", daemon=True)
        self._thread.start()
        log.info("Sensor publishing to Home Assistant enabled.")

    def stop(self) -> None:
        self._stopped.set()
        self._changed.set()

    def notify_change(self) -> None:
        """Request a publication after an inventory change."""
        self._changed.set()

    def publish(self) -> None:
        if not self.config:
            return
        base_url, token = self.config
        for entity_id, state in self.source().items():
            request = urllib.request.Request(
                f"{base_url}/states/{entity_id}",
                data=json.dumps(state).encode(),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10):
                pass

    def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                self.publish()
                if self._failing:
                    log.info("Home Assistant joins again.")
                self._failing = False
            except Exception as exc:  # network error, token refused, Home Assistant restarting…
                if not self._failing:
                    log.warning("Publication to Home Assistant failed: %s", exc)
                self._failing = True
            self._changed.wait(REFRESH_SECONDS)
            self._changed.clear()
            self._stopped.wait(1)  # group changes made in quick succession
