from typing import List
from app.models.schemas import ModuleResult


def run_all_modules(raw_email: str) -> List[ModuleResult]:
    # TODO: remplacer par les vrais appels aux modules CERT
    return [
        ModuleResult(
            module="spf",
            score=20,
            status="fail",
            details="SPF record missing"
        ),
        ModuleResult(
            module="dkim",
            score=10,
            status="warning",
            details="DKIM signature invalid"
        ),
        ModuleResult(
            module="url",
            score=40,
            status="fail",
            details="Malicious URL detected"
        ),
    ]