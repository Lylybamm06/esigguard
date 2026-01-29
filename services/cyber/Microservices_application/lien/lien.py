import json
import os
import re

# Import du parser commun
from common.parser_utils import parse_local_email



# ---------------------------------------------------------
# Extraction des liens
# ---------------------------------------------------------

def extract_links_from_text(text):
    url_regex = r"https?://[A-Za-z0-9\.\-_/=%\?\&]+"
    raw_urls = re.findall(url_regex, text)

    cleaned = []
    for url in raw_urls:
        url = url.split("<")[0].split(">")[0].split('"')[0].split("'")[0]
        if len(url) > 8 and "." in url:
            cleaned.append(url)

    return cleaned


# ---------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------

def analyze_links(parsed_email):
    text = parsed_email.get("content", "")
    urls = extract_links_from_text(text)

    return {
        "email_id": parsed_email.get("email_id"),
        "url_count": len(urls),
        "urls": urls
    }


# ---------------------------------------------------------
# Mode autonome : lecture d’un fichier .eml
# ---------------------------------------------------------

if __name__ == "__main__":
    import os

    
    eml_path = "/data/" + os.getenv("EMAIL_FILE", "email.eml")

    parsed = parse_local_email(eml_path)
    result = analyze_links(parsed)

    # Sauvegarde dans /results
    os.makedirs("/results", exist_ok=True)
    with open("/results/links.json", "w") as f:
        json.dump(result, f, indent=4)

    print("[LINKS] Analyse terminée. Résultat écrit dans /results/links.json")
