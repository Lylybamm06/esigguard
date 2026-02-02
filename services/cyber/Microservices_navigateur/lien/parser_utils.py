from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ---------------------------------------------------------
# PARSEUR NAVIGATEUR — récupère le payload brut
# ---------------------------------------------------------

def parse_browser_payload():
    raw = request.json or {}

    sender = raw.get("sender", {})
    sender_address = sender.get("address", "")
    display_name = sender.get("name", "")

    urls = raw.get("urls", [])
    timestamp = raw.get("timestamp")
    body_snippet = raw.get("body_snippet", "")
    attachments = raw.get("attachments", [])

    # Domaine expéditeur
    domain = sender_address.split("@")[-1] if "@" in sender_address else ""

    # Normalisation timestamp
    try:
        parsed_ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        timestamp_ms = int(parsed_ts.timestamp() * 1000)
    except:
        timestamp_ms = None

    parsed = {
        "email_data": {
            "sender_address": sender_address,
            "display_name": display_name,
            "domain": domain,
            "urls": urls,
            "timestamp": timestamp_ms,
            "body_snippet": body_snippet,
            "attachments": attachments
        }
    }

    return parsed

# ---------------------------------------------------------
# ROUTE API — renvoie uniquement le parsing
# ---------------------------------------------------------

@app.post("/parse")
def parse_only():
    parsed = parse_browser_payload()

    # 🔥 AFFICHAGE DU JSON DANS LE TERMINAL
    print("\n===== PAYLOAD PARSÉ =====")
    print(parsed)
    print("==========================\n")

    return jsonify(parsed)

# ---------------------------------------------------------
# LANCEMENT
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
