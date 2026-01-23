from flask import Flask, request, jsonify
from datetime import datetime
import whois
from parser_utils import parse_browser_payload

app = Flask(__name__)

# ---------------------------------------------------------
# AUTHENTIFICATION — analyse le domaine et calcule le score
# ---------------------------------------------------------
def check_auth(parsed_email):
    """
    Analyse les données standardisées venant du parser navigateur.
    """
    email_data = parsed_email["email_data"]
    sender = email_data["sender_address"]
    display_name = email_data["display_name"]
    domain = email_data["domain"]
    urls = email_data["urls"]
    timestamp = email_data["timestamp"]
    
    score = 0
    details = []
    
    # Analyse du domaine expéditeur
    if not sender:
        score += 30
        details.append("Aucune adresse expéditeur")
    
    if not domain:
        score += 30
        details.append("Domaine expéditeur vide")
    
    # Vérification WHOIS (âge du domaine)
    domain_age_days = None
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
    except:
        details.append("Impossible de récupérer WHOIS")
    
    # Analyse des URLs
    if len(urls) > 3:
        score += 20
        details.append("Trop de liens dans l'email")
    
    # Score final
    pourcentage = min(score, 100)
    
    return {
        "sender_address": sender,
        "domain": domain,
        "domain_age_days": domain_age_days,
        "score": score,
        "pourcentage": pourcentage,
        "details": details,
        "analysis_timestamp": datetime.now().isoformat()
    }

# ---------------------------------------------------------
# ROUTE API — utilise le parseur puis analyse
# ---------------------------------------------------------
@app.post("/analyze")
def analyze_email():
    # 1. Utiliser la fonction de parseur_utils.py
    parsed = parse_browser_payload()
    
    # 2. Analyser avec check_auth
    auth_result = check_auth(parsed)
    
    # 🔥 AFFICHAGE DU JSON DANS LE TERMINAL
    print("\n===== DONNÉES PARSÉES =====")
    print(parsed)
    print("\n===== ANALYSE D'AUTHENTIFICATION =====")
    print(auth_result)
    print("==========================\n")
    
    return jsonify({
        "parsed_data": parsed,
        "authentication_analysis": auth_result
    })

# ---------------------------------------------------------
# LANCEMENT
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
