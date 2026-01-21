import json
import os
import requests

# Import du parser commun
from common.parser_utils import parse_local_email



# ---------------------------------------------------------
# Extraction de l'IP source depuis les Received:
# ---------------------------------------------------------

def extract_source_ip(received_headers):
    """
    On tente d'extraire la première IP trouvée dans les Received:
    C'est souvent l'IP d'origine ou du premier relais.
    """
    import re

    ip_regex = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"

    for header in received_headers:
        match = re.search(ip_regex, header)
        if match:
            return match.group(0)

    return None


# ---------------------------------------------------------
# Vérification VirusTotal (si clé fournie)
# ---------------------------------------------------------

def check_ip_virustotal(ip):
    api_key = os.getenv("VT_API_KEY")
    if not api_key:
        return {"status": "unknown", "reason": "no API key"}

    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
    headers = {"x-apikey": api_key}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        malicious = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {}).get("malicious", 0)

        return {
            "malicious_reports": malicious,
            "status": "malicious" if malicious > 0 else "clean"
        }

    except Exception as e:
        return {"status": "unknown", "error": str(e)}


# ---------------------------------------------------------
# Géolocalisation IP (si clé fournie)
# ---------------------------------------------------------

def geolocate_ip(ip):
    api_key = os.getenv("IP2LOC_API_KEY")
    if not api_key:
        return {"status": "unknown", "reason": "no API key"}

    url = f"https://api.ip2location.io/?key={api_key}&ip={ip}&format=json"

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        return {
            "country": data.get("country_name"),
            "region": data.get("region_name"),
            "city": data.get("city_name"),
            "asn": data.get("asn"),
            "isp": data.get("as"),
            "status": "ok"
        }

    except Exception as e:
        return {"status": "unknown", "error": str(e)}


# ---------------------------------------------------------
# Analyse SMTP globale
# ---------------------------------------------------------

def analyze_smtp(parsed_email):
    received_headers = parsed_email.get("routing", {}).get("received", [])
    source_ip = extract_source_ip(received_headers)

    vt_result = check_ip_virustotal(source_ip) if source_ip else {"status": "unknown"}
    geo_result = geolocate_ip(source_ip) if source_ip else {"status": "unknown"}

    return {
        "email_id": parsed_email.get("email_id"),
        "source_ip": source_ip,
        "virustotal": vt_result,
        "geolocation": geo_result,
        "received_count": len(received_headers),
        "received_headers": received_headers
    }


# ---------------------------------------------------------
# Mode autonome : lecture d’un fichier .eml
# ---------------------------------------------------------

if __name__ == "__main__":
    import os

    

    eml_path = "/data/" + os.getenv("EMAIL_FILE", "email.eml")

    parsed = parse_local_email(eml_path)
    result = analyze_smtp(parsed)

    # Sauvegarde dans /results
    os.makedirs("/results", exist_ok=True)
    with open("/results/smtp.json", "w") as f:
        json.dump(result, f, indent=4)

    print("[SMTP] Analyse terminée. Résultat écrit dans /results/smtp.json")
