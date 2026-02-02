from flask import Flask, jsonify
import os, sys, json, re

sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)

try:
    from groq import Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if GROQ_API_KEY and GROQ_API_KEY != "votre_cle_groq":
        client = Groq(api_key=GROQ_API_KEY)
        GROQ_AVAILABLE = True
    else:
        client = None
        GROQ_AVAILABLE = False
except:
    GROQ_AVAILABLE = False
    client = None

MIME_MAP = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".txt": "text/plain",
    ".zip": "application/zip",
    ".rar": "application/x-rar-compressed",
    ".7z": "application/x-7z-compressed",
    ".exe": "application/x-msdownload",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

SUSPICIOUS_EXTENSIONS = [
    ".exe", ".bat", ".cmd", ".com", ".pif", ".scr",
    ".vbs", ".js", ".jar", ".msi", ".dll"
]

def analyze_mime_verdict(filename, mime_type, extension):
    expected_mime = MIME_MAP.get(extension.lower())
    
    if not expected_mime:
        return {
            "status": "unknown",
            "extension": extension,
            "mime": mime_type,
            "reason": "Extension inconnue"
        }
    
    if expected_mime.lower() == mime_type.lower():
        return {
            "status": "coherent",
            "extension": extension,
            "mime": mime_type,
            "reason": "Extension cohérente"
        }
    else:
        return {
            "status": "incoherent",
            "extension": extension,
            "mime": mime_type,
            "reason": f"Incohérence : attendu {expected_mime}, reçu {mime_type}"
        }

def ai_analyze_attachment(filename, mime_type, extension, size):
    if not GROQ_AVAILABLE or not client:
        return {"status": "unknown", "reason": "IA non disponible"}
    
    prompt = f"""
Analyse cette pièce jointe et réponds STRICTEMENT en JSON sans ```:

{{"status": "coherent" ou "suspect", "reason": "..."}}

Nom : {filename}
MIME : {mime_type}
Extension : {extension}
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        raw = response.choices[0].message.content.strip()
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw).strip()
        result = json.loads(cleaned)
        
        return {
            "status": result.get("status", "unknown"),
            "reason": result.get("reason", "")
        }
    except:
        return {"status": "unknown", "reason": "Erreur IA"}

def analyze_single_attachment(att):
    filename = att.get("filename", "unknown")
    mime_type = att.get("mime_type") or att.get("content_type") or "unknown"
    size = att.get("file_size") or att.get("size") or 0

    extension = ""
    if "." in filename:
        extension = "." + filename.lower().split(".")[-1]

    print(f"  Analyse: {filename} ({extension})")

    mime_verdict = analyze_mime_verdict(filename, mime_type, extension)
    ai_analysis = ai_analyze_attachment(filename, mime_type, extension, size)

    is_dangerous = extension.lower() in SUSPICIOUS_EXTENSIONS

    if mime_verdict.get("status") == "incoherent" and not is_dangerous:
        print("  MIME incohérent → marquage dangereux")
        is_dangerous = True

    score = 0

    if extension.lower() in SUSPICIOUS_EXTENSIONS:
        score += 30

    if mime_verdict.get("status") == "incoherent":
        score += 30

    if ai_analysis.get("status") == "suspect":
        score += 25

    score = min(100, score)

    return {
        "filename": filename,
        "mime_type": mime_type,
        "extension": extension,
        "size": size,
        "mime_verdict": mime_verdict,
        "ai_analysis": ai_analysis,
        "is_dangerous": is_dangerous,
        "score": score
    }

def analyze_attachments(analysis_id):
    print(f"\n FILE - Analyse {analysis_id}")
    
    db = get_db()
    analysis = db.get_complete_analysis(analysis_id)
    
    attachments = analysis.get("attachments", [])

    if not attachments:
        return {
            "analysis_id": analysis_id,
            "service": "file",
            "score": 0,
            "attachment_count": 0,
            "suspicious_count": 0,
            "attachments_analysis": [],
            "explanation": "Aucune pièce jointe"
        }

    attachments_analysis = []
    file_scores = []
    suspicious_count = 0
    suspicious_files = []

    for att in attachments:
        result = analyze_single_attachment(att)
        attachments_analysis.append(result)
        file_scores.append(result["score"])

        db.update_attachment_danger(
            analysis_id,
            result["filename"],
            result["is_dangerous"]
        )

        if result["score"] >= 50:
            suspicious_count += 1
            suspicious_files.append(result["filename"])

    global_score = round(sum(file_scores) / len(file_scores), 2) if file_scores else 0

    if suspicious_count > 0:
        explanation = f"{suspicious_count} fichier(s) suspect(s)"
    else:
        explanation = f"{len(attachments)} fichier(s) analysés, aucun suspect"

    return {
        "analysis_id": analysis_id,
        "service": "file",
        "score": global_score,
        "attachment_count": len(attachments),
        "suspicious_count": suspicious_count,
        "attachments_analysis": attachments_analysis,
        "explanation": explanation
    }

@app.route('/')
def home():
    return jsonify({"service": "File", "port": 5005})

@app.route('/health')
def health():
    try:
        db = get_db()
        conn = db.get_connection()
        conn.close()
        return jsonify({"status": "healthy"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.post("/analyze/<int:analysis_id>")
def analyze(analysis_id):
    try:
        result = analyze_attachments(analysis_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
