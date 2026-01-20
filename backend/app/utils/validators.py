from app.models.schemas import AnalysisRequest


def validate_analysis_request(payload: AnalysisRequest) -> None:
    if not payload.raw_email or len(payload.raw_email) < 10:
        raise ValueError("Le contenu du mail est trop court ou vide.")