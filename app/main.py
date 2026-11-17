"""Web application: REST API and user interface."""

from __future__ import annotations

import html
import re
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, config
from .home_assistant import Publisher, sensor_states
from .inventory import Inventory, InventoryError
from .sheets import SheetError, SheetLibrary, check_id, parse, slugify

INGRESS_PATH_RE = re.compile(r"(/[A-Za-z0-9._~-]+)*")
# Requests that change the inventory or the sheets, and so the sensors.
MUTATING_PREFIXES = ("/api/items", "/api/import", "/api/sheets")


class SheetSource(BaseModel):
    source: str = Field(max_length=500_000)
    id: str | None = None


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


def seed_sheets(directory: Path, examples: Path) -> None:
    """Copy the example sheets into a sheets directory that is still empty."""
    if directory == examples or not examples.is_dir():
        return
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.glob("*.md")):
        return
    for sheet in examples.glob("*.md"):
        shutil.copy2(sheet, directory / sheet.name)
    if (examples / "models").is_dir():
        shutil.copytree(examples / "models", directory / "models", dirs_exist_ok=True)


def create_app(sheets_dir: Path | None = None, db_path: Path | None = None,
               publisher: Publisher | None = None) -> FastAPI:
    sheets_dir = sheets_dir or config.SHEETS_DIR
    db_path = db_path or config.DB_PATH
    library = SheetLibrary(sheets_dir)
    inventory = Inventory(db_path)

    def ha_states() -> dict[str, dict]:
        sheets, _ = library.list()
        return sensor_states({**inventory.summary(), "sheets": len(sheets)}, inventory.list(low_stock=True))

    publisher = publisher or Publisher(ha_states)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        seed_sheets(sheets_dir, config.EXAMPLES_DIR)
        publisher.start()
        yield
        publisher.stop()

    app = FastAPI(title="Prométhée", version=__version__, lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.library, app.state.inventory, app.state.publisher = library, inventory, publisher

    @app.exception_handler(SheetError)
    @app.exception_handler(InventoryError)
    async def domain_error(_: Request, exc: Exception):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.middleware("http")
    async def publish_on_change(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if (request.method != "GET" and response.status_code < 400
                and path.startswith(MUTATING_PREFIXES) and not path.endswith("/preview")):
            publisher.notify_change()
        return response

    # ---------- General ----------

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": __version__}

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

    @app.get("/api/sheets/template", response_class=PlainTextResponse)
    def sheet_template() -> str:
        for path in (sheets_dir / "_template.md", config.EXAMPLES_DIR / "_template.md"):
            if path.is_file():
                return path.read_text(encoding="utf-8")
        return "---\nname: Nouvel appareil\n---\n"

    @app.post("/api/sheets/preview")
    def preview_sheet(body: SheetSource) -> dict[str, Any]:
        return parse(body.id or "preview", body.source).full()

    @app.get("/api/sheets/{sheet_id}")
    def get_sheet(sheet_id: str) -> dict[str, Any]:
        try:
            return library.get(check_id(sheet_id)).full()
        except FileNotFoundError:
            raise HTTPException(404, "Fiche introuvable.") from None

    @app.get("/api/sheets/{sheet_id}/source", response_class=PlainTextResponse)
    def sheet_source(sheet_id: str) -> str:
        try:
            return library.source(sheet_id)
        except FileNotFoundError:
            raise HTTPException(404, "Fiche introuvable.") from None

    @app.post("/api/sheets", status_code=201)
    def create_sheet(body: SheetSource) -> dict[str, Any]:
        sheet_id = body.id or slugify(parse("new", body.source).meta["name"])
        if library.exists(sheet_id):
            raise HTTPException(409, f"Une fiche « {sheet_id} » existe déjà.")
        return library.write(sheet_id, body.source).full()

    @app.put("/api/sheets/{sheet_id}")
    def update_sheet(sheet_id: str, body: SheetSource) -> dict[str, Any]:
        if not library.exists(sheet_id):
            raise HTTPException(404, "Fiche introuvable.")
        return library.write(sheet_id, body.source).full()

    @app.delete("/api/sheets/{sheet_id}", status_code=204)
    def delete_sheet(sheet_id: str) -> Response:
        try:
            library.delete(sheet_id)
        except FileNotFoundError:
            raise HTTPException(404, "Fiche introuvable.") from None
        return Response(status_code=204)

    @app.get("/api/models/{name:path}")
    def get_model(name: str) -> FileResponse:
        try:
            path = library.model_path(name)
        except FileNotFoundError:
            raise HTTPException(404, "Modèle introuvable.") from None
        if not path.is_file():
            raise HTTPException(404, "Modèle introuvable.")
        return FileResponse(path)

    @app.post("/api/models", status_code=201)
    async def upload_model(file: UploadFile = File(...)) -> dict[str, str]:
        content = await file.read(config.MODEL_MAX_BYTES + 1)
        if len(content) > config.MODEL_MAX_BYTES:
            raise HTTPException(413, "Fichier trop volumineux.")
        return {"path": library.save_model(file.filename or "model.glb", content)}

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
