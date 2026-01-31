from flask import Flask, jsonify, request
import json
import os
import requests
from datetime import datetime, UTC
from pathlib import Path
from groq import Groq

print("🔥🔥🔥 LIEN.PY CHARGÉ (VERSION FUSIONNÉE) 🔥🔥🔥")

# ---------------------------------------------------------
# Initialisation du client Groq
# ---------------------------------------------------------

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------------------------------------------------
# Dossier de stockage local
# ---------------------------------------------------------

LINK_STORAGE = Path("./storage/lien")
LINK_STORAGE.mkdir(parents=True, exist_ok=True)

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
# Vérification âge du domaine via WHOIS
# ---------------------------------------------------------

def get_domain_age(domain):
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
    except Exception:
        pass
    
    return {"status": "unknown"}

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
    MAX_SCORE = 130
    score = 0

    # Réputation
    if reputation.get("status") == "not reliable":
        score += 50

    # Âge du domaine
    if domain_age.get("status") == "suspect":
        score += 50

    # Analyse IA
    if ai_analysis.get("status") == "suspect":
        score += 30

    percentage = round((score / MAX_SCORE) * 100, 2)

    return score, percentage

# ---------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------

def check_links(parsed_email):

    links = parsed_email["email_data"].get("urls", [])
    results = []
    total_score = 0

    for raw_url in links:
        raw_url = clean_url(raw_url)
        display_text = raw_url
        domain = raw_url.replace("http://", "").replace("https://", "").split("/")[0]

        reputation = check_domain_reputation(domain)
        age_info = get_domain_age(domain)
        ai_report = ai_analyze_link(display_text, raw_url, domain)

        link_score, link_percentage = calculate_link_score(reputation, age_info, ai_report)
        total_score += link_score

        results.append({
            "url": raw_url,
            "domain": domain,
            "reputation": reputation,
            "domain_age": age_info,
            "ai_analysis": ai_report,
            "score": link_score,
            "percentage": link_percentage,
            "is_suspicious": link_score > 0
        })

    nb_links = len(links)
    average_score = round(total_score / nb_links, 2) if nb_links > 0 else 0
    global_percentage = round((average_score / 130) * 100, 2) if nb_links > 0 else 0

    risk_level = (
        "high" if global_percentage >= 75 else
        "medium" if global_percentage >= 40 else
        "low"
    )

    # Explication simple
    suspect_links = [r["url"] for r in results if r["score"] > 0]
    explanation = (
        f"{len(suspect_links)} lien(s) suspect(s) : "
        f"{', '.join(suspect_links) if suspect_links else 'aucun'}"
    )

    return {
        "links_analysis": results,
        "nb_links": nb_links,
        "score": average_score,
        "percentage": global_percentage,
        "risk_level": risk_level,
        "explanation": explanation
    }

# ---------------------------------------------------------
# Microservice Flask
# ---------------------------------------------------------

app = Flask(__name__)

@app.post("/lien")
def analyze_links():

    parsed = request.get_json(force=True)
    result = check_links(parsed)

    filename = LINK_STORAGE / f"lien_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "parsed_email": parsed,
            "links_analysis": result,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)

    print(f"[LIEN] Analyse sauvegardée dans : {filename}")

    return jsonify(result)

# ---------------------------------------------------------
# Lancement du microservice
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5105)
