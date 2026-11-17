"""Settings read from the environment."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Sheets ship with the application; the variable only helps during development.
SHEETS_DIR = Path(os.environ.get("PROMETHEE_SHEETS_DIR", BASE_DIR / "sheets")).resolve()
DB_DIR = Path(os.environ.get("PROMETHEE_DB_DIR", BASE_DIR / "db")).resolve()
DB_PATH = DB_DIR / "inventory.sqlite3"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Where users ask for new sheets or report errors in existing ones.
REPOSITORY_URL = "https://github.com/astraeos-dev/Promethee"
