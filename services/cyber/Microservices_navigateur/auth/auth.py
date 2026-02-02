from flask import Flask, request, jsonify
from datetime import datetime
import whois
import json
from pathlib import Path

app = Flask(__name__)


AUTH_STORAGE = Path("./storage/auth")
AUTH_STORAGE.mkdir(parents=True, exist_ok=True)


def check_auth(email_data, urls):
    sender = email_data.get("sender_address")
    domain = email_data.get("domain")

    score = 0
    details = []

    
    if not sender:
        score += 30
        details.append("Aucune adresse expéditeur")

    
    if not domain:
        score += 30
        details.append("Domaine expéditeur vide")
    else:
        sender_local, sender_domain = sender.split("@") if "@" in sender else ("", "")
        if sender_domain.lower() != domain.lower():
            score += 20
            details.append("Domaine incohérent avec l'adresse expéditeur")
        else:
            details.append("Domaine cohérent avec l'adresse expéditeur")

    
    domain_age_days = None
    if domain:
        try:
            w = whois.whois(domain)
            creation_date = w.creation_date

            if isinstance(creation_date, list):
                creation_date = creation_date[0]

            if creation_date:
                domain_age_days = (datetime.now() - creation_date).days
                if domain_age_days < 180:
                    score += 40
                    details.append("Domaine trop jeune")
            else:
                score += 40
                details.append("Âge du domaine inconnu")
        except Exception:
            score += 40
            details.append("Impossible de récupérer WHOIS")

    
    if len(urls) > 3:
        score += 20
        details.append("Trop de liens dans l'email")

    explanation = " | ".join(details) if details else "Aucun problème détecté"
    normalized_score = round(score / 120, 2)

    return {
        "score": normalized_score,
        "explanation": explanation,
        "details": details,
        "domain_age_days": domain_age_days,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/auth")
def analyze_email():
    data = request.json or {}

    email_data = data.get("email_data")
    urls = data.get("urls", [])

    if not email_data:
        return jsonify({"error": "email_data manquant dans la requête"}), 400

    auth_result = check_auth(email_data, urls)

    
    filename = AUTH_STORAGE / f"auth_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(auth_result, f, indent=2, ensure_ascii=False)

    print(f"[AUTH] Fichier sauvegardé : {filename}")

    return jsonify(auth_result)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5102)
