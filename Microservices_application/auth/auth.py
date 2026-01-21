import json
import os
import requests
from datetime import datetime, UTC

# Import du parser commun
from common.parser_utils import parse_local_email



# ---------------------------------------------------------
# WHOISXMLAPI — Configuration
# ---------------------------------------------------------

WHOIS_API_KEY = os.getenv("WHOIS_API_KEY")
WHOIS_URL = "https://www.whoisxmlapi.com/whoisserver/WhoisService"


# ---------------------------------------------------------
# WHOIS — Récupération de l'âge du domaine
# ---------------------------------------------------------

def get_domain_age(domain):
    try:
        url = (
            f"{WHOIS_URL}?apiKey={WHOIS_API_KEY}"
            f"&domainName={domain}&outputFormat=JSON"
        )

        r = requests.get(url, timeout=10)
        data = r.json()

        record = data.get("WhoisRecord", {})
        created = record.get("createdDate")

        if not created:
            return {"status": "unknown", "error": "no creation date"}

        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        age_days = (datetime.now(UTC) - created_dt).days
        age_years = age_days / 365

        return {
            "created": created,
            "age_years": round(age_years, 2),
            "status": "bon" if age_years >= 1 else "suspect"
        }

    except Exception as e:
        return {"status": "unknown", "error": str(e)}


# ---------------------------------------------------------
# Comparaison From ↔ Reply-To
# ---------------------------------------------------------

def compare_from_replyto(from_addr, reply_to_addr):
    if not reply_to_addr:
        return "coherent"

    from_domain = from_addr.split("@")[-1] if "@" in from_addr else ""
    reply_domain = reply_to_addr.split("@")[-1] if "@" in reply_to_addr else ""

    return "coherent" if from_domain == reply_domain else "suspect"


# ---------------------------------------------------------
# Comparaison Display Name ↔ Domaine
# ---------------------------------------------------------

def compare_display_name_domain(display_name, domain):
    if not display_name or not domain:
        return "coherent"

    display_lower = display_name.lower()
    domain_root = domain.split(".")[0].lower()

    return "coherent" if domain_root in display_lower else "suspect"


# ---------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------

def check_auth(parsed_email):

    from_addr = parsed_email.get("meta", {}).get("from", {}).get("address", "")
    from_domain = parsed_email.get("meta", {}).get("from", {}).get("domain", "")
    display_name = parsed_email.get("meta", {}).get("from", {}).get("display_name", "")

    reply_to_list = parsed_email.get("meta", {}).get("reply_to", [])
    reply_to_addr = reply_to_list[0].get("address", "") if reply_to_list else ""

    return_path_domain = parsed_email.get("meta", {}).get("return_path", {}).get("domain", "")

    # WHOIS — âge du domaine
    domain_age_info = get_domain_age(from_domain)

    # Résultats initiaux
    spf = parsed_email.get("auth", {}).get("spf", "unknown")
    dkim = parsed_email.get("auth", {}).get("dkim", "unknown")
    dmarc = parsed_email.get("auth", {}).get("dmarc", "unknown")

    from_vs_return_path = "coherent" if from_domain == return_path_domain else "different"
    from_vs_replyto = compare_from_replyto(from_addr, reply_to_addr)
    display_name_vs_domain = compare_display_name_domain(display_name, from_domain)

    # SCORE
    score = 0

    if spf != "pass":
        score += 25
    if dkim != "pass":
        score += 25
    if dmarc != "pass":
        score += 25
    if from_vs_return_path != "coherent":
        score += 30
    if from_vs_replyto != "coherent":
        score += 30
    if display_name_vs_domain != "coherent":
        score += 40
    if domain_age_info.get("status") != "bon":
        score += 25

    pourcentage = (score / 200) * 100

    return {
        "email_id": parsed_email.get("email_id"),

        "spf": spf,
        "dkim": dkim,
        "dmarc": dmarc,

        "from_address": from_addr,
        "reply_to_address": reply_to_addr,
        "return_path_domain": return_path_domain,

        "from_vs_return_path": from_vs_return_path,
        "from_vs_replyto": from_vs_replyto,
        "display_name_vs_domain": display_name_vs_domain,

        "domain_age": domain_age_info,
        "analysis_timestamp": datetime.now(UTC).isoformat(),

        "score": score,
        "pourcentage": round(pourcentage, 2)
    }


# ---------------------------------------------------------
# Mode autonome : lecture d’un fichier .eml
# ---------------------------------------------------------

if __name__ == "__main__":
    import os

    

    eml_path = "/data/" + os.getenv("EMAIL_FILE", "email.eml")


    parsed = parse_local_email(eml_path)
    result = check_auth(parsed)

    # Sauvegarde dans /results
    os.makedirs("/results", exist_ok=True)
    with open("/results/auth.json", "w") as f:
        json.dump(result, f, indent=4)

    print("[AUTH] Analyse terminée. Résultat écrit dans /results/auth.json")
