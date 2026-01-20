from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_analysis, routes_history, routes_stats
from app.core.config import settings

app = FastAPI(
    title="ESIG'Guard API",
    version="1.0.0",
    description="API d'analyse et de scoring de mails de phishing."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_analysis.router, prefix="/analyse", tags=["Analyse"])
app.include_router(routes_history.router, prefix="/historique", tags=["Historique"])
app.include_router(routes_stats.router, prefix="/stats", tags=["Statistiques"])


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {"status": "ok"}