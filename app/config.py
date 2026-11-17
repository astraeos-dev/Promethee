"""Settings read from the environment."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SHEETS_DIR = Path(os.environ.get("PROMETHEE_SHEETS_DIR", BASE_DIR / "sheets")).resolve()
DB_DIR = Path(os.environ.get("PROMETHEE_DB_DIR", BASE_DIR / "db")).resolve()
EXAMPLES_DIR = Path(os.environ.get("PROMETHEE_EXAMPLES_DIR", BASE_DIR / "sheets")).resolve()
DB_PATH = DB_DIR / "inventory.sqlite3"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Maximum size of an uploaded 3D model, in bytes.
MODEL_MAX_BYTES = int(os.environ.get("PROMETHEE_MODEL_MAX_BYTES", 30 * 1024 * 1024))
