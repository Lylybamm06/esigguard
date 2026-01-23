from flask import Flask, jsonify
import json
import os
import requests
from datetime import datetime, UTC
from groq import Groq

from parser_utils import parse_browser_payload

# ---------------------------------------------------------
# Initialisation du client Groq
# ---------------------------------------------------------

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------------------------------------------------
# Nettoyage des URLs cassées
# ---------------------------------------------------------

def clean_url(url):
    if not url:
        return ""
    for sep in ['"', "'", "<", ">", ")"]:
        if sep in url:
            url = url.split(sep)[0]
    return url.strip()

# ---------------------------------------------------------
# Vérification réputation du domaine via VirusTotal
# ---------------------------------------------------------

def check_domain_reputation(domain):
    try:
        api_key = os.getenv("VT_API_KEY")
        url = f"https://www.virustotal.com/api/v3/domains/{domain}"
        headers = {"x-apikey": api_key}

        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            data = r.json()
            malicious = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {}).get("malicious", 0)
            status = "reliable" if malicious == 0 else "not reliable"

            return {
                "domain": domain,
                "status": status,
                "malicious_reports": malicious
            }

    except Exception as e:
        return {"domain": domain, "status": "unknown", "error": str(e)}

    return {"domain": domain, "status": "unknown"}

# ---------------------------------------------------------
# Vérification âge du domaine via WHOIS XML API + fallback python-whois
# ---------------------------------------------------------

def get_domain_age(domain):
    # Essai avec WHOIS XML API
    try:
        api_key = os.getenv("WHOIS_API_KEY")
        
        if api_key:
            url = (
                "https://www.whoisxmlapi.com/whoisserver/WhoisService"
                f"?apiKey={api_key}&domainName={domain}&outputFormat=JSON"
            )

            r = requests.get(url, timeout=5)
            data = r.json()

            record = data.get("WhoisRecord", {})

            created_date = (
                record.get("createdDate")
                or record.get("registryData", {}).get("createdDate")
            )

            if created_date:
                created = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                age_days = (datetime.now(UTC) - created).days
                age_years = age_days / 365

                status = "bon" if age_years >= 1 else "suspect"

                return {
                    "created": created_date,
                    "age_years": round(age_years, 2),
                    "status": status
                }
    except Exception as e:
        pass
    
    # Fallback avec python-whois
    try:
        import whois
        w = whois.whois(domain)
        creation_date = w.creation_date
        
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        
        if creation_date:
            age_days = (datetime.now(UTC) - creation_date.replace(tzinfo=UTC)).days
            age_years = age_days / 365
            
            status = "bon" if age_years >= 1 else "suspect"
            
            return {
                "created": creation_date.isoformat(),
                "age_years": round(age_years, 2),
                "status": status
            }
    except Exception as e:
        return {"status": "unknown", "error": str(e)}
    
    return {"status": "unknown", "error": "no creation date"}

# ---------------------------------------------------------
# Analyse IA du lien via Groq
# ---------------------------------------------------------

def ai_analyze_link(display_text, raw_url, domain):
    prompt = f"""
    Analyse ce lien :

    - Texte affiché : {display_text}
    - URL réelle : {raw_url}
    - Domaine : {domain}

    Dis si le lien est 'coherent' ou 'suspect'.
    Donne une raison explicite.

    Réponds STRICTEMENT en JSON SANS ``` :
    {{
        "status": "...",
        "reason": "..."
    }}
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception:
        return {
            "status": "unknown",
            "reason": f"Invalid JSON returned by Groq: {raw}"
        }

# ---------------------------------------------------------
# Calcul du score pour un lien
# ---------------------------------------------------------

def calculate_link_score(reputation, domain_age, ai_analysis):
    """
    Calcule le score de phishing pour un lien
    - reputation not reliable : +50 points
    - domain_age suspect : +50 points
    - ai_analysis suspect : +30 points
    Score maximum par lien : 130 points
    """
    MAX_SCORE = 130
    score = 0
    details = []
    
    # Vérifier la réputation
    if reputation.get("status") == "not reliable":
        score += 50
        details.append({
            "indicator": "reputation",
            "points": 50,
            "reason": f"Domaine non fiable ({reputation.get('malicious_reports', 0)} rapports malveillants)"
        })
    
    # Vérifier l'âge du domaine
    if domain_age.get("status") == "suspect":
        score += 50
        details.append({
            "indicator": "domain_age",
            "points": 50,
            "reason": f"Domaine trop récent ({domain_age.get('age_years', 0)} ans)"
        })
    
    # Vérifier l'analyse IA
    if ai_analysis.get("status") == "suspect":
        score += 30
        details.append({
            "indicator": "ai_analysis",
            "points": 30,
            "reason": ai_analysis.get("reason", "Lien suspect selon l'IA")
        })
    
    # Calculer le pourcentage pour ce lien
    percentage = round((score / MAX_SCORE) * 100, 2)
    
    return score, percentage, details

# ---------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------

def check_links(parsed_email):

    links = parsed_email["email_data"].get("urls", [])
    results = []
    total_score = 0
    link_count = len(links)

    for raw_url in links:
        raw_url = clean_url(raw_url)
        display_text = raw_url

        domain = raw_url.replace("http://", "").replace("https://", "").split("/")[0]

        reputation = check_domain_reputation(domain)
        age_info = get_domain_age(domain)
        ai_report = ai_analyze_link(display_text, raw_url, domain)
        
        # Calculer le score pour ce lien
        link_score, link_percentage, score_details = calculate_link_score(reputation, age_info, ai_report)
        total_score += link_score

        results.append({
            "raw_url": raw_url,
            "display_text": display_text,
            "domain": domain,
            "reputation": reputation,
            "domain_age": age_info,
            "ai_analysis": ai_report,
            "link_score": link_score,
            "link_percentage": link_percentage,
            "score_details": score_details,
            "risk_level": "high" if link_percentage >= 75 else "medium" if link_percentage >= 40 else "low"
        })
    
    # Calculer la moyenne des scores
    average_score = round(total_score / link_count, 2) if link_count > 0 else 0
    
    # Calculer le pourcentage global : moyenne_score / 130 * 100
    global_percentage = round((average_score / 130) * 100, 2) if link_count > 0 else 0

    return {
        "link_analysis": results,
        "summary": {
            "total_links": link_count,
            "total_score": total_score,
            "average_score": average_score,
            "global_percentage": global_percentage,
            "risk_level": "high" if global_percentage >= 75 else "medium" if global_percentage >= 40 else "low"
        }
    }

# ---------------------------------------------------------
# Microservice Flask (pas de RabbitMQ)
# ---------------------------------------------------------

app = Flask(__name__)

@app.post("/links")
def analyze_links():
    parsed = parse_browser_payload()  # ← récupère request.json automatiquement
    result = check_links(parsed)
    
    # 🔥 AFFICHAGE DANS LE TERMINAL
    print("\n===== DONNÉES PARSÉES =====")
    print(f"Expéditeur: {parsed['email_data']['sender_address']}")
    print(f"Nombre de liens: {len(parsed['email_data'].get('urls', []))}")
    
    print("\n===== ANALYSE DES LIENS =====")
    for i, link in enumerate(result['link_analysis'], 1):
        print(f"\n[Lien {i}] {link['raw_url']}")
        print(f"  Score: {link['link_score']}/130 ({link['link_percentage']}%)")
        print(f"  Risque: {link['risk_level']}")
        if link['score_details']:
            print(f"  Détails:")
            for detail in link['score_details']:
                print(f"    - {detail['indicator']}: +{detail['points']} ({detail['reason']})")
    
    print(f"\n===== RÉSUMÉ GLOBAL =====")
    print(f"Nombre de liens analysés: {result['summary']['total_links']}")
    print(f"Score total: {result['summary']['total_score']}")
    print(f"Score moyen: {result['summary']['average_score']}/130")
    print(f"Pourcentage global: {result['summary']['global_percentage']}%")
    print(f"Niveau de risque: {result['summary']['risk_level']}")
    print("==========================\n")
    
    return jsonify(result)

# ---------------------------------------------------------
# Lancement du microservice
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
