"""
File Service - Version améliorée avec JSON détaillé et analyse IA
Port : 5005
"""

from flask import Flask, jsonify
import os, sys, json, re

sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)

# Import conditionnel de Groq
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

# Mapping extension → MIME type attendu
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

# Extensions suspectes
SUSPICIOUS_EXTENSIONS = [
    ".exe", ".bat", ".cmd", ".com", ".pif", ".scr", 
    ".vbs", ".js", ".jar", ".msi", ".dll"
]

def analyze_mime_verdict(filename, mime_type, extension):
    """Analyse cohérence extension/MIME"""
    expected_mime = MIME_MAP.get(extension.lower())
    
    if not expected_mime:
        # Extension inconnue
        return {
            "status": "unknown",
            "extension": extension,
            "mime": mime_type,
            "reason": "Extension inconnue, impossible de valider"
        }
    
    if expected_mime.lower() == mime_type.lower():
        return {
            "status": "coherent",
            "extension": extension,
            "mime": mime_type,
            "reason": "L'extension correspond au type MIME"
        }
    else:
        return {
            "status": "incoherent",
            "extension": extension,
            "mime": mime_type,
            "reason": f"Incohérence : attendu {expected_mime}, reçu {mime_type}"
        }

def ai_analyze_attachment(filename, mime_type, extension, size):
    """Analyse IA de la pièce jointe avec Groq"""
    if not GROQ_AVAILABLE or not client:
        return {
            "status": "unknown",
            "reason": "Analyse IA non disponible"
        }
    
    prompt = f"""
Analyse cette pièce jointe et réponds STRICTEMENT en JSON sans ```:

{{"status": "coherent" ou "suspect", "reason": "..."}}

Règles :
- "coherent" si le fichier semble légitime
- "suspect" si type de fichier dangereux, nom bizarre, ou incohérence

Fichier à analyser :
- Nom : {filename}
- Type MIME : {mime_type}
- Extension : {extension}

Réponds UNIQUEMENT avec le JSON.
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        raw = response.choices[0].message.content.strip()
        
        # Nettoyer JSON
        cleaned = raw
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()
        
        result = json.loads(cleaned)
        
        return {
            "status": result.get("status", "unknown"),
            "reason": result.get("reason", "Analyse IA disponible")
        }
    except Exception as e:
        print(f"⚠️  Erreur IA: {e}")
        return {
            "status": "unknown",
            "reason": f"Erreur IA: {str(e)[:50]}"
        }

def analyze_single_attachment(att):
    """Analyse complète d'une pièce jointe"""
    filename = att.get("filename", "unknown")
    mime_type = att.get("mime_type") or att.get("content_type") or  "unknown"
    
    size = att.get("file_size") or att.get("size") or 0
    
    # Extraire extension
    extension = ""
    if "." in filename:
        extension = "." + filename.lower().split(".")[-1]
    
    print(f"  📎 Analyse: {filename} ({extension})")
    
    # Analyse MIME verdict
    mime_verdict = analyze_mime_verdict(filename, mime_type, extension)
    
    # Analyse IA
    ai_analysis = ai_analyze_attachment(filename, mime_type, extension, size)
    
    # Calcul score
    score = 0
    
    # Extension suspecte (+30)
    if extension.lower() in SUSPICIOUS_EXTENSIONS:
        score += 30
        print(f"    ⚠️  Extension suspecte: +30")
    
    # MIME incohérent (+30)
    if mime_verdict.get("status") == "incoherent":
        score += 30
        print(f"    ⚠️  MIME incohérent: +30")
    
    # IA suspect (+25)
    if ai_analysis.get("status") == "suspect":
        score += 25
        print(f"    ⚠️  IA suspect: +25")
    
    score = min(100, score)
    
    print(f"    Score: {score}/100")
    
    return {
        "filename": filename,
        "mime_type": mime_type,
        "extension": extension,
        "size": size,
        "mime_verdict": mime_verdict,
        "ai_analysis": ai_analysis,
        "score": score
    }

def analyze_attachments(analysis_id):
    """Analyse toutes les pièces jointes"""
    print(f"\n📎 FILE - Analyse {analysis_id}")
    
    db = get_db()
    analysis = db.get_complete_analysis(analysis_id)
    
    if not analysis:
        raise ValueError(f"Analyse {analysis_id} introuvable")
    
    attachments = analysis.get("attachments", [])
    
    if not attachments:
        print("  ℹ️  Aucune pièce jointe")
        return {
            "analysis_id": analysis_id,
            "service": "file",
            "score": 0,
            "attachment_count": 0,
            "suspicious_count": 0,
            "attachments_analysis": [],
            "explanation": "File : Aucune piece jointe"
        }
    
    print(f"  📊 {len(attachments)} fichier(s) trouvé(s)")
    
    # Analyser chaque fichier
    attachments_analysis = []
    file_scores = []
    suspicious_count = 0
    suspicious_files = []
    
    for att in attachments:
        analysis_result = analyze_single_attachment(att)
        attachments_analysis.append(analysis_result)
        file_scores.append(analysis_result["score"])
        
        if analysis_result["score"] >= 50:
            suspicious_count += 1
            suspicious_files.append(analysis_result["filename"])
    
    # Score global : moyenne des scores
    if file_scores:
        global_score = round(sum(file_scores) / len(file_scores), 2)
    else:
        global_score = 0
    
    # Explication
    if suspicious_count > 0:
        if len(suspicious_files) <= 2:
            file_list = ", ".join(suspicious_files)
        else:
            file_list = f"{suspicious_files[0]}, {suspicious_files[1]} et {len(suspicious_files)-2} autre(s)"
        
        explanation = f"File : {suspicious_count} fichier(s) suspects ({file_list})"
    else:
        explanation = f"File : {len(attachments)} fichier(s) analysé(s), aucun suspect"
    
    print(f"  📊 Score global: {global_score}/100")
    print(f"  ⚠️  {suspicious_count} fichier(s) suspect(s)")
    
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
        print(f"❌ Erreur: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "="*60)
    print("📎 File Service - Port 5005")
    print("Version améliorée avec JSON détaillé et IA")
    print("="*60)
    
    if GROQ_AVAILABLE:
        print("✅ Groq API: Disponible")
    else:
        print("⚠️  Groq API: Non disponible (analyse IA désactivée)")
    
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=5005, debug=True)
