from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ModuleResult(BaseModel):
    module: str = Field(..., description="Nom du module (spf, dkim, url, etc.)")
    score: int = Field(..., ge=0, le=100)
    status: Literal["ok", "warning", "fail"]
    details: str


class AnalysisRequest(BaseModel):
    raw_email: str = Field(..., description="Contenu brut du mail (RFC822).")


class AnalysisResponse(BaseModel):
    id: int
    global_score: int
    classification: Literal["safe", "suspicious", "dangerous"]
    modules: List[ModuleResult]
    created_at: datetime


class HistoryItem(BaseModel):
    id: int
    global_score: int
    classification: str
    created_at: datetime


class StatsResponse(BaseModel):
    total_emails: int
    dangerous: int
    suspicious: int
    safe: int
    top_domains: list[str]
    timeline: list[dict]