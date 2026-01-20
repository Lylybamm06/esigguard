from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Analysis
from app.models.schemas import StatsResponse

router = APIRouter()


@router.get("/", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)) -> StatsResponse:
    total = db.query(Analysis).count()
    dangerous = db.query(Analysis).filter(Analysis.classification == "dangerous").count()
    suspicious = db.query(Analysis).filter(Analysis.classification == "suspicious").count()
    safe = db.query(Analysis).filter(Analysis.classification == "safe").count()

    # Placeholder : à remplacer par de vraies stats Big Data
    top_domains: list[str] = []
    timeline: list[dict] = []

    return StatsResponse(
        total_emails=total,
        dangerous=dangerous,
        suspicious=suspicious,
        safe=safe,
        top_domains=top_domains,
        timeline=timeline,
    )