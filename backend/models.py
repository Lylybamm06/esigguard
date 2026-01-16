from pydantic import BaseModel
from typing import List

class EmailInput(BaseModel):
    sender: str
    subject: str
    body: str
    links: List[str]
    has_attachments: bool

class ScoreResult(BaseModel):
    score: int
    risk_level: str
    reasons: List[str]
