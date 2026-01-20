from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.schemas import AnalysisRequest, AnalysisResponse
from app.models.entities import Analysis
from app.db.session import get_db
from app.services.cyber_orchestrator import run_all_modules
from app.core.scoring import compute_global_score, classify
from app.core.security import compute_email_fingerprint
from app.utils.logger import logger

router = APIRouter()


@router.post("/", response_model=AnalysisResponse)
def analyse_email(payload: AnalysisRequest, db: Session = Depends(get_db)) -> AnalysisResponse:
    try:
        fingerprint = compute_email_fingerprint(payload.raw_email)
        modules = run_all_modules(payload.raw_email)
        global_score = compute_global_score(modules)
        classification = classify(global_score)

        analysis = Analysis(
            fingerprint=fingerprint,
            global_score=global_score,
            classification=classification,
            modules=[m.dict() for m in modules],
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        logger.info(f"New analysis stored with id={analysis.id}")

        return AnalysisResponse(
            id=analysis.id,
            global_score=analysis.global_score,
            classification=analysis.classification,
            modules=modules,
            created_at=analysis.created_at or datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'analyse du mail."
        )