from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from ..auth_tokens import get_current_user
from ..db import get_db

router = APIRouter(tags=["stats"])  # <-- PAS de prefix ici


@router.get("/stats")
def get_stats(user: str = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()

    cutoff_24h = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    cutoff_7d = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    # Emails uploaded in last 24h
    cur.execute(
        "SELECT COUNT(*) AS c FROM analyses WHERE upload_date >= ?",
        (cutoff_24h,),
    )
    emails_24h = cur.fetchone()["c"]

    # Threats detected in last 24h (verdict contains risky keywords)
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM analyses
        WHERE upload_date >= ?
          AND final_verdict IS NOT NULL
          AND (
            LOWER(final_verdict) LIKE '%phish%'
            OR LOWER(final_verdict) LIKE '%sus%'
            OR LOWER(final_verdict) LIKE '%critical%'
            OR LOWER(final_verdict) LIKE '%danger%'
          )
        """,
        (cutoff_24h,),
    )
    threats_24h = cur.fetchone()["c"]

    # "Blocked" = final_score >= 60 (tu peux changer le seuil ici)
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM analyses
        WHERE upload_date >= ?
          AND final_score IS NOT NULL
          AND final_score >= 60
        """,
        (cutoff_24h,),
    )
    blocked_24h = cur.fetchone()["c"]

    # Global risk score = average final_score last 7 days
    cur.execute(
        """
        SELECT AVG(final_score) AS avg_score
        FROM analyses
        WHERE upload_date >= ?
          AND final_score IS NOT NULL
        """,
        (cutoff_7d,),
    )
    avg_score = cur.fetchone()["avg_score"]
    global_risk = int(round(avg_score)) if avg_score is not None else 0

    # Latest critical = highest score last 7 days
    cur.execute(
        """
        SELECT id, final_verdict, final_score, human_explanation
        FROM analyses
        WHERE upload_date >= ?
          AND final_score IS NOT NULL
        ORDER BY final_score DESC
        LIMIT 1
        """,
        (cutoff_7d,),
    )
    latest_row = cur.fetchone()
    latest = dict(latest_row) if latest_row else {}

    conn.close()

    return {
        "cards": {
            "emails_24h": emails_24h,
            "threats_24h": threats_24h,
            "blocked_24h": blocked_24h,
            "global_risk": global_risk,
        },
        "latest_critical": {
            "id": latest.get("id"),
            "final_verdict": latest.get("final_verdict"),
            "final_score": latest.get("final_score"),
            "explanation": latest.get("human_explanation"),
        },
    }
