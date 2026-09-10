import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from .db import init_db

# Crée le fichier SQLite et les tables au démarrage si elles n'existent pas encore.
init_db()

app = FastAPI(title="ESIG'GUARD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .api.analyses import router as analyses_router
from .api.upload import router as upload_router
from .api.stats import router as stats_router
from .api.score import router as score_router
from .auth_router import router as auth_router

@app.get("/ping")
def ping():
    return {"ping": "pong"}

@app.get("/api/version")
def version():
    return {
        "app": "esigguard",
        "signature": "MARYLYNE_BACK_V1",
        "utc": datetime.utcnow().isoformat(),
        "db_backend": "sqlite",
    }

app.include_router(analyses_router, prefix="/api", tags=["analyses"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(stats_router, prefix="/api", tags=["stats"])
app.include_router(auth_router, prefix="/api", tags=["auth"])
# Sans préfixe : c'est l'URL que l'extension Chrome appelle directement.
app.include_router(score_router)
