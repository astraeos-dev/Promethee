"""Web application: REST API and user interface."""

from __future__ import annotations

import html
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, config
from .catalog import Catalog, correction_url, request_url
from .home_assistant import Publisher, sensor_states
from .inventory import Inventory, InventoryError
from .sheets import SheetError, SheetLibrary, check_id

INGRESS_PATH_RE = re.compile(r"(/[A-Za-z0-9._~-]+)*")
# Requests that change the inventory, and so the sensors.
MUTATING_PREFIXES = ("/api/items", "/api/import")
MODEL_CACHE_SECONDS = 24 * 3600


class ItemIn(BaseModel):
    name: str | None = None
    category: str | None = None
    value: str | None = None
    package: str | None = None
    sheet: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    threshold: int | None = Field(default=None, ge=0)
    location: str | None = None
    supplier: str | None = None
    price: float | None = None
    notes: str | None = None


class MovementIn(BaseModel):
    delta: int
    reason: str = ""


def create_app(sheets_dir: Path | None = None, db_path: Path | None = None,
               publisher: Publisher | None = None) -> FastAPI:
    sheets_dir = sheets_dir or config.SHEETS_DIR
    db_path = db_path or config.DB_PATH
    library = SheetLibrary(sheets_dir)
    catalog = Catalog(sheets_dir / "catalog.yaml")
    inventory = Inventory(db_path)

    def ha_states() -> dict[str, dict]:
        sheets, _ = library.list()
        return sensor_states({**inventory.summary(), "sheets": len(sheets)}, inventory.list(low_stock=True))

    publisher = publisher or Publisher(ha_states)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        publisher.start()
        yield
        publisher.stop()

    app = FastAPI(title="Prométhée", version=__version__, lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.library, app.state.inventory, app.state.publisher = library, inventory, publisher
    # 3D models and Three.js shrink about four times: it matters through Ingress or on a Pi.
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)

    @app.exception_handler(SheetError)
    @app.exception_handler(InventoryError)
    async def domain_error(_: Request, exc: Exception):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.middleware("http")
    async def publish_on_change(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if request.method != "GET" and response.status_code < 400 and path.startswith(MUTATING_PREFIXES):
            publisher.notify_change()
        return response

    # ---------- General ----------

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/about")
    def about() -> dict[str, Any]:
        return {"version": __version__, "repository": config.REPOSITORY_URL}

    @app.get("/api/summary")
    def summary() -> dict[str, Any]:
        sheets, errors = library.list()
        return {**inventory.summary(), "sheets": len(sheets), "sheets_with_errors": len(errors)}

    @app.get("/api/alerts")
    def alerts() -> list[dict]:
        return inventory.list(low_stock=True)

    # ---------- Sheets ----------

    @app.get("/api/sheets")
    def list_sheets() -> dict[str, Any]:
        sheets, errors = library.list()
        return {"sheets": [s.summary() for s in sheets], "errors": errors}

    @app.get("/api/sheets/{sheet_id}")
    def get_sheet(sheet_id: str) -> dict[str, Any]:
        try:
            sheet = library.get(check_id(sheet_id))
        except FileNotFoundError:
            raise HTTPException(404, "Fiche introuvable.") from None
        return {**sheet.full(), "correction_url": correction_url(config.REPOSITORY_URL, sheet.id, sheet.meta["name"])}

    @app.get("/api/catalog")
    def hardware_catalog() -> dict[str, Any]:
        """Common hardware offered by "Demander une fiche", with pre-filled request links."""
        existing = {sheet.id for sheet in library.list()[0]}
        devices = [
            {**device, "has_sheet": device["id"] in existing, "request_url": request_url(config.REPOSITORY_URL, device)}
            for device in catalog.devices()
        ]
        return {
            "devices": devices,
            "categories": list(dict.fromkeys(device["category"] for device in devices)),
            "other_request_url": request_url(config.REPOSITORY_URL),
        }

    @app.api_route("/api/models/{name:path}", methods=["GET", "HEAD"])
    def get_model(name: str) -> FileResponse:
        try:
            path = library.model_path(name)
        except FileNotFoundError:
            raise HTTPException(404, "Modèle introuvable.") from None
        if not path.is_file():
            raise HTTPException(404, "Modèle introuvable.")
        return FileResponse(path, media_type="model/gltf-binary",
                            headers={"Cache-Control": f"public, max-age={MODEL_CACHE_SECONDS}"})

    # ---------- Inventory ----------

    def get_item_or_404(item_id: int) -> dict:
        try:
            return inventory.get(item_id)
        except KeyError:
            raise HTTPException(404, "Article introuvable.") from None

    @app.get("/api/items")
    def list_items(q: str = "", category: str = "", sheet: str = "",
                   low_stock: bool = Query(False)) -> list[dict]:
        return inventory.list(query=q.strip(), category=category, sheet=sheet, low_stock=low_stock)

    @app.get("/api/categories")
    def categories() -> dict[str, list[str]]:
        sheets, _ = library.list()
        return {"items": inventory.categories(),
                "sheets": sorted({s.meta["category"] for s in sheets}, key=str.lower)}

    @app.post("/api/items", status_code=201)
    def create_item(item: ItemIn) -> dict:
        return inventory.create(item.model_dump(exclude_unset=True))

    @app.get("/api/items/{item_id}")
    def get_item(item_id: int) -> dict:
        return get_item_or_404(item_id)

    @app.put("/api/items/{item_id}")
    def update_item(item_id: int, item: ItemIn) -> dict:
        get_item_or_404(item_id)
        return inventory.update(item_id, item.model_dump(exclude_unset=True))

    @app.delete("/api/items/{item_id}", status_code=204)
    def delete_item(item_id: int) -> Response:
        try:
            inventory.delete(item_id)
        except KeyError:
            raise HTTPException(404, "Article introuvable.") from None
        return Response(status_code=204)

    @app.post("/api/items/{item_id}/movements")
    def add_movement(item_id: int, movement: MovementIn) -> dict:
        get_item_or_404(item_id)
        return inventory.move(item_id, movement.delta, movement.reason)

    @app.get("/api/items/{item_id}/movements")
    def list_movements(item_id: int) -> list[dict]:
        get_item_or_404(item_id)
        return inventory.history(item_id)

    @app.get("/api/export.csv")
    def export_csv() -> Response:
        return Response("﻿" + inventory.export_csv(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="promethee-stock.csv"'})

    @app.post("/api/import")
    async def import_csv(file: UploadFile = File(...)) -> dict[str, int]:
        content = await file.read(5 * 1024 * 1024)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        return inventory.import_csv(text)

    # ---------- User interface ----------

    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index(request: Request) -> HTMLResponse:
        # Behind Home Assistant Ingress the UI is served under a prefix
        # (/api/hassio_ingress/<token>) given in the X-Ingress-Path header.
        prefix = request.headers.get("x-ingress-path", "").rstrip("/")
        if not INGRESS_PATH_RE.fullmatch(prefix):
            prefix = ""
        page = (config.STATIC_DIR / "index.html").read_text(encoding="utf-8")
        page = page.replace('<base href="/">', f'<base href="{html.escape(prefix)}/">', 1)
        return HTMLResponse(page, headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
