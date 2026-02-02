from flask import Flask, jsonify, request
import json
import os
from datetime import datetime
from pathlib import Path


FILE_STORAGE = Path("./storage/file")
FILE_STORAGE.mkdir(parents=True, exist_ok=True)

def get_extension(filename):
    filename = filename.lower()
    if "." not in filename:
        return ""
    return filename[filename.rfind("."):]


def ai_analyze_attachment(filename, content_type, size):
    ext = get_extension(filename)

    suspect_ext = [
        ".exe", ".js", ".vbs", ".scr", ".bat", ".cmd",
        ".jar", ".zip", ".rar", ".7z", ".iso"
    ]

    macro_ext = [
        ".docm", ".xlsm", ".pptm",
        ".dotm", ".xltm", ".potm", ".docx"
    ]

    if ext in suspect_ext or ext in macro_ext:
        return {
            "status": "suspect",
            "reason": "extension dangereuse"
        }

    return {
        "status": "coherent",
        "reason": f"L’extension {ext} ne fait pas partie des extensions dangereuses ou à macros."
    }


def calculate_attachment_score(ai_analysis):
    MAX_SCORE = 100
    score = 0
    details = []

    if ai_analysis.get("status") == "suspect":
        score += 100
        details.append({
            "indicator": "ai_analysis",
            "points": 100,
            "reason": ai_analysis.get("reason", "extension dangereuse")
        })

    percentage = round((score / MAX_SCORE) * 100, 2)
    return score, percentage, details


def check_attachments(parsed_email):

    attachments = parsed_email.get("email_data", {}).get("attachments", [])
    results = []
    total_score = 0
    count = len(attachments)

    suspect_files = []

    for att in attachments:
        
        if isinstance(att, dict):
            filename = att.get("filename", "inconnu")
            content_type = att.get("content_type", "inconnu")
            size = att.get("size", 0)
        elif isinstance(att, str):
            filename = att
            content_type = "inconnu"
            size = 0
        else:
            filename = "inconnu"
            content_type = "inconnu"
            size = 0

        ai_report = ai_analyze_attachment(filename, content_type, size)
        score, percentage, details = calculate_attachment_score(ai_report)
        total_score += score

        if ai_report["status"] == "suspect":
            suspect_files.append(filename)

        results.append({
            "filename": filename,
            "content_type": content_type,
            "size": size,
            "ai_analysis": ai_report,
            "score": score,
            "percentage": percentage,
            "score_details": details,
            "risk_level": "high" if percentage >= 75 else "medium" if percentage >= 40 else "low"
        })

    average_percentage = round((total_score / (count * 100)) * 100, 2) if count > 0 else 0

    if suspect_files:
        explanation_text = (
            f"{len(suspect_files)} fichiers suspects : {', '.join(suspect_files)} "
            f"| Raison : Extensions dangereuses"
        )
    else:
        explanation_text = "0 fichier suspect | Raison : Aucune extension dangereuse détectée"

    return {
        "attachment_analysis": results,
        "nb_attachments": count,
        "moyenne_pourcentage": average_percentage,
        "Explanation": explanation_text
    }


app = Flask(__name__)

@app.post("/files")
def analyze_files():
    parsed = request.get_json(force=True)
    result = check_attachments(parsed)

    filename = FILE_STORAGE / f"file_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "parsed_email": parsed,
            "attachment_analysis": result,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)

    print(f"[FILE] Analyse sauvegardée dans : {filename}")
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5104)
