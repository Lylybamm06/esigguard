import json
import os

RESULTS_DIR = "/results"

def load_json(name):
    path = os.path.join(RESULTS_DIR, name)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

if __name__ == "__main__":
    # Charger les JSON AVANT de les utiliser
    parsed = load_json("parsed.json")
    auth = load_json("auth.json")
    smtp = load_json("smtp.json")

    # Nettoyage du subject
    raw_subject = parsed.get("headers", {}).get("raw_subject", "")
    clean_subject = raw_subject.replace("\\n", "\n").replace("\\r", "\n")

    # Construction du rapport final
    final = {
        "email_id": parsed.get("headers", {}).get("message_id", ""),
        "parsed": {
            "headers": parsed.get("headers", {}),
            "meta": parsed.get("meta", {}),
            "auth": {
                "spf": auth.get("spf", ""),
                "dkim": auth.get("dkim", ""),
                "dmarc": auth.get("dmarc", "")
            },
            "routing": {
                "received": smtp.get("received", []),
                "hops": smtp.get("hops", 0)
            },
            "content": {
                "subject": clean_subject,
                "body": parsed.get("content", "")
            }
        }
    }

    # Écriture du rapport final
    with open(os.path.join(RESULTS_DIR, "final_report.json"), "w", encoding="utf-8") as f:
        json.dump(final, f, indent=4, ensure_ascii=False)

    print("[REPORT] Rapport final généré dans /results/final_report.json")
