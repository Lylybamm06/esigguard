from flask import Flask, jsonify
from groq import Groq
import os
import json
import logging
from parser_utils import parse_browser_payload

# =========================================================
# 1) Configuration des logs
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ContentNavigateur] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ContentNavigateur")

# =========================================================
# 2) Initialisation du client Groq
# =========================================================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# =========================================================
# 3) Fonction d'analyse IA
# =========================================================
def ai_analyze_content(body_snippet, known_banks=None):
    prompt = f"""
    Analyse ce mail selon trois axes et renvoie STRICTEMENT le JSON suivant :
    {{
      "global_verdict": "...",
      "phishing_indicators": {{
        "status": "...",
        "reason": "..."
      }},
      "language_quality": {{
        "status": "...",
        "reason": "..."
      }},
      "context_coherence": {{
        "status": "...",
        "reason": "..."
      }}
    }}
    
    Règles :
    - "status" = "ok" ou "suspect"
    - "reason" = une phrase expliquant pourquoi
    - "global_verdict" = "coherent" si tout est ok, sinon "suspect"
    
    Extrait du corps : {body_snippet}
    Banques connues : {known_banks if known_banks else "non spécifiées"}
    
    Réponds UNIQUEMENT avec le JSON strict.
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()

# =========================================================
# 4) Calcul du score de phishing
# =========================================================
def calculate_phishing_score(ai_json):
    """
    Calcule le score de phishing basé sur l'analyse IA
    - phishing_indicators suspect : +15 points
    - language_quality suspect : +15 points
    - context_coherence suspect : +30 points
    Score maximum : 60 points
    """
    MAX_SCORE = 60
    score = 0
    details = []
    
    # Vérifier phishing_indicators
    if ai_json.get("phishing_indicators", {}).get("status") == "suspect":
        score += 15
        details.append({
            "indicator": "phishing_indicators",
            "points": 15,
            "reason": ai_json["phishing_indicators"].get("reason", "Indicateurs de phishing détectés")
        })
    
    # Vérifier language_quality
    if ai_json.get("language_quality", {}).get("status") != "ok":
        score += 15
        details.append({
            "indicator": "language_quality",
            "points": 15,
            "reason": ai_json["language_quality"].get("reason", "Qualité de langue suspecte")
        })
    
    # Vérifier context_coherence
    if ai_json.get("context_coherence", {}).get("status") == "suspect":
        score += 30
        details.append({
            "indicator": "context_coherence",
            "points": 30,
            "reason": ai_json["context_coherence"].get("reason", "Incohérence contextuelle détectée")
        })
    
    # Calculer le pourcentage
    percentage = round((score / MAX_SCORE) * 100, 2)
    
    return score, percentage, details

# =========================================================
# 5) Traitement du contenu + Sécurisation JSON
# =========================================================
def check_content(parsed_email, known_banks=None):
    body_snippet = parsed_email["email_data"].get("body_snippet", "")
    
    ai_report = ai_analyze_content(body_snippet, known_banks)
    
    cleaned = ai_report.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")[1:]
        if lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    
    try:
        ai_json = json.loads(cleaned)
    except Exception:
        ai_json = {
            "global_verdict": "error",
            "phishing_indicators": {"status": "error", "reason": "IA returned invalid JSON"},
            "language_quality": {"status": "error", "reason": "IA returned invalid JSON"},
            "context_coherence": {"status": "error", "reason": "IA returned invalid JSON"}
        }
    
    # Calculer le score de phishing et le pourcentage
    phishing_score, phishing_percentage, score_details = calculate_phishing_score(ai_json)
    
    return {
        "ai_content_analysis": ai_json,
        "phishing_score": phishing_score,
        "phishing_percentage": phishing_percentage,
        "score_details": score_details,
        "risk_level": "high" if phishing_percentage >= 75 else "medium" if phishing_percentage >= 33 else "low"
    }

# =========================================================
# 6) Microservice Flask (pas de RabbitMQ)
# =========================================================
app = Flask(__name__)

@app.post("/content")
def analyze_content():
    parsed = parse_browser_payload()  # ← récupère request.json automatiquement
    known_banks = ["BNP Paribas", "Société Générale", "La Banque Postale"]
    
    result = check_content(parsed, known_banks)
    
    # 🔥 AFFICHAGE DANS LE TERMINAL
    print("\n===== DONNÉES PARSÉES =====")
    print(f"Expéditeur: {parsed['email_data']['sender_address']}")
    print(f"Domaine: {parsed['email_data']['domain']}")
    print(f"Corps: {parsed['email_data']['body_snippet']}")
    print(f"URLs: {parsed['email_data']['urls']}")
    
    print("\n===== ANALYSE IA DU CONTENU =====")
    print(json.dumps(result['ai_content_analysis'], indent=2, ensure_ascii=False))
    
    print("\n===== SCORE DE PHISHING =====")
    print(f"Score total: {result['phishing_score']}/60 ({result['phishing_percentage']}%)")
    print(f"Niveau de risque: {result['risk_level']}")
    print("\nDétails du scoring:")
    for detail in result['score_details']:
        print(f"  - {detail['indicator']}: +{detail['points']} points ({detail['reason']})")
    print("==========================\n")
    
    return jsonify(result)

# =========================================================
# 7) Lancement du microservice
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
