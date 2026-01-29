"""
Auth Service - Version améliorée avec JSON détaillé
Port : 5003
"""

from flask import Flask, jsonify
import os, sys, requests
from datetime import datetime, timezone
from dateutil import parser

sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)

WHOIS_API_KEY = os.getenv("WHOIS_API_KEY")
WHOIS_URL = "https://www.whoisxmlapi.com/whoisserver/WhoisService"


# ---------------------------------------------------------
# WHOIS — Calcul âge du domaine (corrigé)
# ---------------------------------------------------------
def get_domain_age(domain):
    if not WHOIS_API_KEY or WHOIS_API_KEY == "votre_cle_whois":
        return {
            "domain": domain,
            "age_years": None,
            "status": "unknown",
            "created_date": None
        }

    try:
        url = f"{WHOIS_URL}?apiKey={WHOIS_API_KEY}&domainName={domain}&outputFormat=JSON"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return {
                "domain": domain,
                "age_years": None,
                "status": "unknown",
                "created_date": None
            }

        data = r.json()
        record = data.get("WhoisRecord", {})
        created_date = record.get("createdDate") or record.get("registryData", {}).get("createdDate")

        if not created_date:
            return {
                "domain": domain,
                "age_years": None,
                "status": "unknown",
                "created_date": None
            }

        # Correction timezone
        created = parser.parse(created_date)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        age_years = (datetime.now(timezone.utc) - created).days / 365

        return {
            "domain": domain,
            "age_years": round(age_years, 2),
            "status": "bon" if age_years >= 1 else "suspect",
            "created_date": created_date
        }

    except Exception as e:
        print(f"⚠  Erreur WHOIS: {e}")
        return {
            "domain": domain,
            "age_years": None,
            "status": "unknown",
            "created_date": None
        }


# ---------------------------------------------------------
# ANALYSE AUTHENTIFICATION
# ---------------------------------------------------------
def analyze_auth(analysis_id):
    print(f"\n🔐 AUTH - Analyse {analysis_id}")

    db = get_db()
    a = db.get_complete_analysis(analysis_id)

    if not a:
        raise ValueError(f"Analyse {analysis_id} introuvable")

    from_addr = a.get('email_sender', '')
    from_domain = from_addr.split('@')[-1] if '@' in from_addr else ''
    display_name = a.get('display_name', '')
    reply_to = a.get('reply_to', '')
    return_path = a.get('return_path', '')

    print(f"  📧 From: {from_addr}")
    print(f"  🏷  Display: {display_name}")
    print(f"  🌐 Domaine: {from_domain}")

    spf = a.get('auth_spf', 'unknown')
    dkim = a.get('auth_dkim', 'unknown')
    dmarc = a.get('auth_dmarc', 'unknown')

    print(f"  🔒 SPF: {spf}, DKIM: {dkim}, DMARC: {dmarc}")

    domain_age = get_domain_age(from_domain)

    score = 0
    issues = []

    # SPF
    spf_status = {"protocol": "SPF", "status": spf, "score": 0}
    if spf == "fail":
        score += 25
        spf_status["score"] = 25
        issues.append("SPF:fail")
    elif spf == "unknown":
        score += 10
        spf_status["score"] = 10
        issues.append("SPF:unknown")

    # DKIM
    dkim_status = {"protocol": "DKIM", "status": dkim, "score": 0}
    if dkim == "fail":
        score += 25
        dkim_status["score"] = 25
        issues.append("DKIM:fail")
    elif dkim == "unknown":
        score += 10
        dkim_status["score"] = 10
        issues.append("DKIM:unknown")

    # DMARC
    dmarc_status = {"protocol": "DMARC", "status": dmarc, "score": 0}
    if dmarc == "fail":
        score += 25
        dmarc_status["score"] = 25
        issues.append("DMARC:fail")
    elif dmarc == "unknown":
        score += 10
        dmarc_status["score"] = 10
        issues.append("DMARC:unknown")

    # From vs Return-Path
    return_domain = return_path.split('@')[-1] if '@' in return_path else from_domain
    from_vs_return = {
        "from_domain": from_domain,
        "return_domain": return_domain,
        "status": "coherent" if from_domain == return_domain else "incoherent",
        "score": 0
    }
    if from_domain != return_domain:
        score += 30
        from_vs_return["score"] = 30
        issues.append("FromVsReturn: incoherent")

    # From vs Reply-To
    from_vs_reply = {
        "from_domain": from_domain,
        "reply_domain": None,
        "status": "coherent",
        "score": 0
    }
    if reply_to:
        reply_domain = reply_to.split('@')[-1]
        from_vs_reply["reply_domain"] = reply_domain
        if reply_domain != from_domain:
            score += 30
            from_vs_reply["status"] = "incoherent"
            from_vs_reply["score"] = 30
            issues.append("FromVsReply: incoherent")

    # Display Name vs Domain
    display_vs_domain = {
        "display_name": display_name,
        "from_domain": from_domain,
        "status": "coherent",
        "score": 0
    }
    if display_name:
        domain_base = from_domain.split('.')[0].lower()
        if domain_base not in display_name.lower():
            score += 40
            display_vs_domain["status"] = "incoherent"
            display_vs_domain["score"] = 40
            issues.append("DisplayNameVsDomain: incoherent")

    # Âge domaine
    if domain_age["status"] == "suspect":
        score += 25
        issues.append("AgeDomaine: suspect")
    elif domain_age["status"] == "unknown":
        score += 10
        issues.append("AgeDomaine: inconnu")

    final_score = min(100, int((score / 200) * 100))
    explanation = "Authentification : " + " | ".join(issues)

    print(f"  📊 Score: {final_score}/100")

    # ---------------------------------------------------------
    # AFFICHAGE
    # ---------------------------------------------------------
    return {
        "analysis_id": analysis_id,
        "spf": spf_status,
        "dkim": dkim_status,
        "dmarc": dmarc_status,
        "domain_age": domain_age,
        "display_vs_domain": display_vs_domain,
        "from_vs_reply": from_vs_reply,
        "from_vs_return": from_vs_return,
        "score": final_score,
        "explanation": explanation
    }


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------
@app.route('/')
def home():
    return jsonify({"service": "Auth", "port": 5003})

@app.route('/health')
def health():
    try:
        db = get_db()
        conn = db.get_connection()
        conn.close()
        return jsonify({"status": "healthy"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.post("/analyze/<int:analysis_id>")
def analyze(analysis_id):
    try:
        result = analyze_auth(analysis_id)
        return jsonify(result)
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔐 Auth Service - Port 5003")
    print("Version améliorée avec JSON détaillé")
    print("="*60 + "\n")

    app.run(host="0.0.0.0", port=5003, debug=True)
