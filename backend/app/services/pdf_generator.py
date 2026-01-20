from datetime import datetime
from typing import List
from app.models.schemas import ModuleResult, AnalysisResponse


def generate_report(analysis: AnalysisResponse) -> bytes:
    # Placeholder : ici tu pourras utiliser reportlab, weasyprint, etc.
    content_lines: List[str] = [
        f"ESIG'Guard - Rapport d'analyse",
        f"ID: {analysis.id}",
        f"Date: {analysis.created_at.isoformat()}",
        f"Score global: {analysis.global_score}",
        f"Classification: {analysis.classification}",
        "",
        "Détails des modules :",
    ]
    for m in analysis.modules:
        content_lines.append(f"- {m.module}: {m.status} ({m.score}) -> {m.details}")

    content = "\n".join(content_lines)
    return content.encode("utf-8")