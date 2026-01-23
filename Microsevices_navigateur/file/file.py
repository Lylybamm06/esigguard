from flask import Flask, jsonify
import json
from parser_utils import parse_browser_payload

# ---------------------------------------------------------
# Microservice Flask
# ---------------------------------------------------------
app = Flask(__name__)

# ---------------------------------------------------------
# Analyse des pièces jointes côté navigateur
# ---------------------------------------------------------
def analyze_attachments(parsed_email):
    attachments = parsed_email["email_data"].get("attachments", [])
    results = []
    total_score = 0
    
    # Extensions suspectes (navigateur)
    suspect_ext = [".exe", ".js", ".vbs", ".scr", ".bat", ".cmd", ".jar", ".zip", ".rar", ".7z", ".iso"]
    
    for att in attachments:
        filename = att if isinstance(att, str) else att.get("filename", "unknown")
        score = 0
        
        # Vérification extension
        for ext in suspect_ext:
            if filename.lower().endswith(ext):
                score += 70
                break
        
        pourcentage = min(100, score)
        total_score += pourcentage
        
        results.append({
            "filename": filename,
            "score": score,
            "pourcentage": round(pourcentage, 2),
            "risk_type": "suspect" if score > 0 else "normal"
        })
    
    moyenne = total_score / len(attachments) if attachments else 0
    
    return {
        "nb_attachments": len(attachments),
        "attachment_analysis": results,
        "moyenne_pourcentage": round(moyenne, 2)
    }

# ---------------------------------------------------------
# Route API /files
# ---------------------------------------------------------
@app.post("/files")
def analyze_files():
    parsed = parse_browser_payload()  # ← récupère request.json automatiquement
    result = analyze_attachments(parsed)
    
    # 🔥 AFFICHAGE DANS LE TERMINAL
    print("\n===== DONNÉES PARSÉES =====")
    print(f"Expéditeur: {parsed['email_data']['sender_address']}")
    print(f"Nombre de pièces jointes: {len(parsed['email_data'].get('attachments', []))}")
    
    print("\n===== ANALYSE DES PIÈCES JOINTES =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("==========================\n")
    
    return jsonify(result)

# ---------------------------------------------------------
# Lancement du microservice
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
