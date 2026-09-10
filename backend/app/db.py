import os
import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / os.getenv("SQLITE_DB_FILE", "esigguard.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    status            TEXT NOT NULL DEFAULT 'pending',
    raw_file_path     TEXT,
    upload_date       TEXT NOT NULL,
    final_score       INTEGER,
    final_verdict     TEXT,
    human_explanation TEXT
);
"""


def get_db() -> sqlite3.Connection:
    """Retourne une connexion à la base SQLite locale (backend/esigguard.db).

    Base de données locale, sans serveur à installer : le fichier est créé
    automatiquement au premier démarrage (voir init_db). Remplace l'ancienne
    base MySQL Azure (service décommissionné, plus accessible).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crée les tables si elles n'existent pas encore. Appelé au démarrage de l'API."""
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
