import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth_tokens import get_current_user
from ..db import get_db
from ..services.email_parser import parse_eml_file
from ..services.ml_scoring import score_email

router = APIRouter()


@router.post("/upload")
async def upload_email(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    try:
        # 1) Nom sécurisé
        original_name = file.filename or "email.eml"
        safe_name = re.sub(r"[^\w\-_.]", "_", original_name)
        if not safe_name.lower().endswith(".eml"):
            safe_name += ".eml"

        # 2) Sauvegarde locale (conservée pour archive/relecture, ignorée par git)
        local_dir = Path("data-mails/raw")
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / safe_name

        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3) Parsing + scoring en local (modèle ML — voir services/ml_scoring.py).
        #    Remplace l'ancien envoi vers une VM Azure dédiée (service décommissionné,
        #    voir services/ssh_transfer.py conservé pour référence).
        parsed = parse_eml_file(str(local_path))
        result = score_email(
            subject=parsed["subject"],
            body=parsed["body"],
            links=parsed["links"],
            has_attachments=parsed["has_attachments"],
        )

        # 4) Insertion DB (analyse déjà terminée, pas de statut "pending")
        conn = get_db()
        cursor = conn.cursor()

        human_explanation = " ; ".join(result["reasons"])

        cursor.execute(
            """
            INSERT INTO analyses
                (status, raw_file_path, upload_date, final_score, final_verdict, human_explanation)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "done",
                str(local_path),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                result["score"],
                result["risk_level"],
                human_explanation,
            ),
        )
        conn.commit()

        analysis_id = cursor.lastrowid

        conn.close()

        return {
            "message": "Analyse terminée",
            "analysis_id": analysis_id,
            "status": "done",
            "score": result["score"],
            "risk_level": result["risk_level"],
            "reasons": result["reasons"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
