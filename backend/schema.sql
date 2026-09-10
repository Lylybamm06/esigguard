-- Schéma de la base SQLite d'ESIG'Guard.
-- Pour information seulement : ces tables sont créées automatiquement au
-- démarrage de l'API (voir backend/app/db.py, fonction init_db) dans le
-- fichier backend/esigguard.db. Rien à exécuter manuellement.

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
