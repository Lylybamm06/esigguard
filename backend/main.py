from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="ESIG'Guard API")

class ScoreRequest(BaseModel):
    sender: str
    subject: str
    body: str
    links: List[str] = []
    has_attachments: bool = False

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/score")
def score(req: ScoreRequest):
    score = 0
    reasons = []

    if "urgent" in req.subject.lower():
        score += 25
        reasons.append("Objet contient un mot d'urgence")

    if len(req.links) >= 3:
        score += 15
        reasons.append("Beaucoup de liens détectés")

    if req.has_attachments:
        score += 10
        reasons.append("Présence de pièce jointe")

    if score >= 71:
        risk = "red"
    elif score >= 31:
        risk = "orange"
    else:
        risk = "green"

    return {
        "score": min(score, 100),
        "risk_level": risk,
        "reasons": reasons
    }
