from fastapi import APIRouter, Depends, HTTPException

from ..auth_tokens import get_current_user
from ..db import get_db

router = APIRouter(tags=["analyses"])


@router.get("/analyses")
def get_analyses(user: str = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            status,
            upload_date,
            final_score,
            final_verdict
        FROM analyses
        ORDER BY id DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]

    conn.close()
    return rows


@router.get("/analyses/{analysis_id}")
def get_analysis_by_id(analysis_id: int, user: str = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            status,
            upload_date,
            final_score,
            final_verdict,
            human_explanation
        FROM analyses
        WHERE id = ?
        """,
        (analysis_id,),
    )
    row = cur.fetchone()

    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return dict(row)
