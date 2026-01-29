import json
import os

# Import du parser commun
from common.parser_utils import parse_local_email



# ---------------------------------------------------------
# Analyse des pièces jointes
# ---------------------------------------------------------

def analyze_attachments(parsed_email):
    attachments = parsed_email.get("attachments", [])

    results = []

    for att in attachments:
        results.append({
            "filename": att.get("filename"),
            "content_type": att.get("content_type"),
            "size_bytes": att.get("size")
        })

    return {
        "email_id": parsed_email.get("email_id"),
        "attachment_count": len(results),
        "attachments": results
    }


# ---------------------------------------------------------
# Mode autonome : lecture d’un fichier .eml
# ---------------------------------------------------------

if __name__ == "__main__":
    import os

    
    eml_path = "/data/" + os.getenv("EMAIL_FILE", "email.eml")

    parsed = parse_local_email(eml_path)
    result = analyze_attachments(parsed)

    # Sauvegarde dans /results
    os.makedirs("/results", exist_ok=True)
    with open("/results/files.json", "w") as f:
        json.dump(result, f, indent=4)

    print("[FILE] Analyse terminée. Résultat écrit dans /results/files.json")
