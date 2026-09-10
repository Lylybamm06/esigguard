from fastapi import APIRouter
from pydantic import BaseModel

from ..services.ml_scoring import score_email

# Pas de préfixe "/api" ici : l'extension navigateur (extension/popup.js)
# appelle directement http://127.0.0.1:8000/score.
router = APIRouter(tags=["score"])


class ScoreRequest(BaseModel):
    sender: str = ""
    subject: str = ""
    body: str = ""
    links: list[str] = []
    has_attachments: bool = False


@router.post("/score")
def score(payload: ScoreRequest):
    return score_email(
        subject=payload.subject,
        body=payload.body,
        links=payload.links,
        has_attachments=payload.has_attachments,
    )
