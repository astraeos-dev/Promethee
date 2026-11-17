"""Configuration lue dans l'environnement."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

FICHES_DIR = Path(os.environ.get("PROMETHEE_FICHES", BASE_DIR / "fiches")).resolve()
DATA_DIR = Path(os.environ.get("PROMETHEE_DATA", BASE_DIR / "data")).resolve()
EXEMPLES_DIR = Path(os.environ.get("PROMETHEE_EXEMPLES", BASE_DIR / "fiches")).resolve()
DB_PATH = DATA_DIR / "stock.sqlite3"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Taille maximale d'un modèle 3D téléversé (octets).
MODELE_MAX = int(os.environ.get("PROMETHEE_MODELE_MAX", 30 * 1024 * 1024))
