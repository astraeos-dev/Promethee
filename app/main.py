"""Application web : API REST et interface."""

from __future__ import annotations

import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, config
from .fiches import Bibliotheque, FicheError, analyser, slug, verifier_id
from .stock import Stock, StockError


class SourceFiche(BaseModel):
    source: str = Field(max_length=500_000)
    id: str | None = None


class Article(BaseModel):
    nom: str | None = None
    categorie: str | None = None
    valeur: str | None = None
    boitier: str | None = None
    fiche: str | None = None
    quantite: int | None = Field(default=None, ge=0)
    seuil: int | None = Field(default=None, ge=0)
    emplacement: str | None = None
    fournisseur: str | None = None
    prix: float | None = None
    notes: str | None = None


class Mouvement(BaseModel):
    delta: int
    motif: str = ""


def amorcer_fiches(dossier: Path, exemples: Path) -> None:
    """Copie les fiches d'exemple dans un dossier de fiches encore vide."""
    if dossier == exemples or not exemples.is_dir():
        return
    dossier.mkdir(parents=True, exist_ok=True)
    if any(dossier.glob("*.md")):
        return
    for f in exemples.glob("*.md"):
        shutil.copy2(f, dossier / f.name)
    if (exemples / "modeles").is_dir():
        shutil.copytree(exemples / "modeles", dossier / "modeles", dirs_exist_ok=True)


def creer_app(dossier_fiches: Path | None = None, base: Path | None = None) -> FastAPI:
    dossier_fiches = dossier_fiches or config.FICHES_DIR
    base = base or config.DB_PATH

    @asynccontextmanager
    async def cycle(app: FastAPI):
        amorcer_fiches(dossier_fiches, config.EXEMPLES_DIR)
        yield

    app = FastAPI(title="Prométhée", version=__version__, lifespan=cycle,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    biblio = Bibliotheque(dossier_fiches)
    stock = Stock(base)
    app.state.biblio, app.state.stock = biblio, stock

    @app.exception_handler(FicheError)
    @app.exception_handler(StockError)
    async def erreur_metier(_: Request, exc: Exception):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    # ---------- Général ----------

    @app.get("/api/sante")
    def sante() -> dict[str, Any]:
        return {"statut": "ok", "version": __version__}

    @app.get("/api/resume")
    def resume() -> dict[str, Any]:
        fiches, erreurs = biblio.lister()
        return {**stock.resume(), "fiches": len(fiches), "fiches_en_erreur": len(erreurs)}

    # ---------- Fiches ----------

    @app.get("/api/fiches")
    def lister_fiches() -> dict[str, Any]:
        fiches, erreurs = biblio.lister()
        return {"fiches": [f.resume() for f in fiches], "erreurs": erreurs}

    @app.get("/api/fiches/modele-vierge", response_class=PlainTextResponse)
    def modele_vierge() -> str:
        chemin = dossier_fiches / "_modele.md"
        if not chemin.is_file():
            chemin = config.EXEMPLES_DIR / "_modele.md"
        return chemin.read_text(encoding="utf-8") if chemin.is_file() else "---\nnom: Nouvel appareil\n---\n"

    @app.post("/api/fiches/apercu")
    def apercu(corps: SourceFiche) -> dict[str, Any]:
        return analyser(corps.id or "apercu", corps.source).complete()

    @app.get("/api/fiches/{id_}")
    def lire_fiche(id_: str) -> dict[str, Any]:
        try:
            return biblio.lire(verifier_id(id_)).complete()
        except FileNotFoundError:
            raise HTTPException(404, "Fiche introuvable.") from None

    @app.get("/api/fiches/{id_}/source", response_class=PlainTextResponse)
    def source_fiche(id_: str) -> str:
        try:
            return biblio.source(id_)
        except FileNotFoundError:
            raise HTTPException(404, "Fiche introuvable.") from None

    @app.post("/api/fiches", status_code=201)
    def creer_fiche(corps: SourceFiche) -> dict[str, Any]:
        id_ = corps.id or slug(analyser("nouvelle", corps.source).meta["nom"])
        if biblio.existe(id_):
            raise HTTPException(409, f"Une fiche « {id_} » existe déjà.")
        return biblio.ecrire(id_, corps.source).complete()

    @app.put("/api/fiches/{id_}")
    def modifier_fiche(id_: str, corps: SourceFiche) -> dict[str, Any]:
        if not biblio.existe(id_):
            raise HTTPException(404, "Fiche introuvable.")
        return biblio.ecrire(id_, corps.source).complete()

    @app.delete("/api/fiches/{id_}", status_code=204)
    def supprimer_fiche(id_: str) -> Response:
        try:
            biblio.supprimer(id_)
        except FileNotFoundError:
            raise HTTPException(404, "Fiche introuvable.") from None
        return Response(status_code=204)

    @app.get("/api/modeles/{nom:path}")
    def lire_modele(nom: str) -> FileResponse:
        try:
            chemin = biblio.chemin_modele(nom)
        except FileNotFoundError:
            raise HTTPException(404, "Modèle introuvable.") from None
        if not chemin.is_file():
            raise HTTPException(404, "Modèle introuvable.")
        return FileResponse(chemin)

    @app.post("/api/modeles", status_code=201)
    async def televerser_modele(fichier: UploadFile = File(...)) -> dict[str, str]:
        contenu = await fichier.read(config.MODELE_MAX + 1)
        if len(contenu) > config.MODELE_MAX:
            raise HTTPException(413, "Fichier trop volumineux.")
        return {"chemin": biblio.ecrire_modele(fichier.filename or "modele.glb", contenu)}

    # ---------- Stock ----------

    def _article(id_: int) -> dict:
        try:
            return stock.lire(id_)
        except KeyError:
            raise HTTPException(404, "Article introuvable.") from None

    @app.get("/api/articles")
    def lister_articles(q: str = "", categorie: str = "", fiche: str = "",
                        alerte: bool = Query(False)) -> list[dict]:
        return stock.lister(q=q.strip(), categorie=categorie, fiche=fiche, alerte=alerte)

    @app.get("/api/categories")
    def categories() -> dict[str, list[str]]:
        fiches, _ = biblio.lister()
        return {"stock": stock.categories(),
                "fiches": sorted({f.meta["categorie"] for f in fiches}, key=str.lower)}

    @app.post("/api/articles", status_code=201)
    def creer_article(a: Article) -> dict:
        return stock.creer(a.model_dump(exclude_unset=True))

    @app.get("/api/articles/{id_}")
    def lire_article(id_: int) -> dict:
        return _article(id_)

    @app.put("/api/articles/{id_}")
    def modifier_article(id_: int, a: Article) -> dict:
        _article(id_)
        return stock.modifier(id_, a.model_dump(exclude_unset=True))

    @app.delete("/api/articles/{id_}", status_code=204)
    def supprimer_article(id_: int) -> Response:
        try:
            stock.supprimer(id_)
        except KeyError:
            raise HTTPException(404, "Article introuvable.") from None
        return Response(status_code=204)

    @app.post("/api/articles/{id_}/mouvements")
    def mouvement(id_: int, m: Mouvement) -> dict:
        _article(id_)
        return stock.mouvement(id_, m.delta, m.motif)

    @app.get("/api/articles/{id_}/mouvements")
    def historique(id_: int) -> list[dict]:
        _article(id_)
        return stock.historique(id_)

    @app.get("/api/export.csv")
    def exporter() -> Response:
        return Response("﻿" + stock.exporter_csv(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="promethee-stock.csv"'})

    @app.post("/api/import")
    async def importer(fichier: UploadFile = File(...)) -> dict[str, int]:
        contenu = await fichier.read(5 * 1024 * 1024)
        try:
            texte = contenu.decode("utf-8")
        except UnicodeDecodeError:
            texte = contenu.decode("latin-1")
        return stock.importer_csv(texte)

    # ---------- Interface ----------

    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def accueil() -> FileResponse:
        return FileResponse(config.STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = creer_app()
