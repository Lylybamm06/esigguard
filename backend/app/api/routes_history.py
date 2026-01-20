from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Analysis
from app.models.schemas import HistoryItem

router = APIRouter()


@router.get("/", response_model=List[HistoryItem])
def get_history(db: Session = Depends(get_db)) -> List[HistoryItem]:
    analyses = db.query(Analysis).order_by(Analysis.created_at.desc()).limit(100).all()
    return [
        HistoryItem(
            id=a.id,
            global_score=a.global_score,
            classification=a.classification,
            created_at=a.created_at,
        )
        for a in analyses
    ]