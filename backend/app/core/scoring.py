from typing import List
from app.models.schemas import ModuleResult


def compute_global_score(modules: List[ModuleResult]) -> int:
    total = sum(m.score for m in modules)
    return max(0, min(total, 100))


def classify(score: int) -> str:
    if score < 30:
        return "safe"
    if score < 70:
        return "suspicious"
    return "dangerous"