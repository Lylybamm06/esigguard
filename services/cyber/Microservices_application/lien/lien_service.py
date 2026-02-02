"""
Lien Service - Version améliorée avec JSON détaillé
Port : 5004
"""

from flask import Flask, jsonify
import os, sys, json, requests, re
from datetime import datetime, UTC
from urllib.parse import urlparse

sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)

# Import conditionnel de Groq
try:
    from groq import Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if GROQ_API_KEY and GROQ_API_KEY != "votre_cle_groq":
        client = Groq(api_key=GROQ_API_KEY)
        GROQ_AVAILABLE = True
    else:
        client = None
        GROQ_AVAILABLE = False
except:
    GROQ_AVAILABLE = False
    client = None


def clean_url(url: str) -> str:
    if not url:
        return ""
    for sep in ['"', "'", "<", ">", ")"]:
        if sep in url:
            url = url.split(sep)[0]
    return url.strip()


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        return domain.lower()
    except:
        return url


def check_domain_reputation(domain: str) -> dict:
    try:
        api_key = os.getenv("VT_API_KEY")
        if not api_key or api_key == "votre_cle_virustotal":
            return {"domain": domain, "status": "unknown", "malicious_reports": 0}

        url = f"https://www.virustotal.com/api/v3/domains/{domain}"
        headers = {"x-apikey": api_key}
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code == 200:
            data = r.json()
            stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)

            status = "not reliable" if malicious > 0 else "reliable"

            return {
                "domain": domain,
                "status": status,
                "malicious_reports": malicious
            }

        return {"domain": domain, "status": "unknown", "malicious_reports": 0}

    except Exception as e:
        print(f"⚠  Erreur VirusTotal: {e}")
        return {"domain": domain, "status": "unknown", "malicious_reports": 0}


def get_domain_age(domain: str) -> dict:
    try:
        api_key = os.getenv("WHOIS_API_KEY")
        if not api_key or api_key == "votre_cle_whois":
            return {"status": "unknown"}

        url = f"https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey={api_key}&domainName={domain}&outputFormat=JSON"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return {"status": "unknown"}

        data = r.json()
        record = data.get("WhoisRecord", {})
        created_date = record.get("createdDate") or record.get("registryData", {}).get("createdDate")

        if not created_date:
            return {"status": "unknown"}

        created = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
        age_years = (datetime.now(UTC) - created).days / 365

        return {
            "created": created_date,
            "age_years": round(age_years, 2),
            "status": "bon" if age_years >= 1 else "suspect"
        }

    except Exception as e:
        print(f"⚠  Erreur WHOIS: {e}")
        return {"status": "unknown"}


def ai_analyze_link(display_text: str, raw_url: str, domain: str) -> dict:
    if not GROQ_AVAILABLE or not client:
        return {"status": "unknown", "reason": "Analyse IA non disponible"}

    prompt = f"""
Analyse ce lien et réponds STRICTEMENT en JSON sans ```:

{{"status": "coherent" ou "suspect", "reason": "..."}}

Texte affiché : {display_text}
URL réelle : {raw_url}
Domaine : {domain}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )

        raw = response.choices[0].message.content.strip()
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw).strip()
        result = json.loads(cleaned)

        return {
            "status": result.get("status", "unknown"),
            "reason": result.get("reason", "")
        }

    except Exception as e:
	        print(f"⚠  Erreur IA: {e}")
        return {"status": "unknown", "reason": "Erreur IA"}


def analyze_url(url: str) -> dict:
    print(f"  🔗 Analyse: {url[:60]}...")

    url = clean_url(url)
    domain = extract_domain(url)

    reputation = check_domain_reputation(domain)
    domain_age = get_domain_age(domain)
    ai_analysis = ai_analyze_link(url, url, domain)

    # Score brut (max théorique = 130)
    raw_score = 0

    if reputation.get("status") == "not reliable":
        raw_score += 50

    age_status = domain_age.get("status")
    if age_status == "suspect":
        raw_score += 50
    elif age_status == "unknown":
        raw_score += 25

    if ai_analysis.get("status") == "suspect":
        raw_score += 30

    # Normalisation sur 100
    url_score = int((raw_score / 130) * 100)
    url_score = min(100, url_score)

    print(f"    Score: {url_score}/100")

    return {
        "raw_url": url,
        "display_text": url,
        "domain": domain,
        "reputation": reputation,
        "domain_age": domain_age,
        "ai_analysis": ai_analysis,
        "score": url_score
    }


def analyze_liens(analysis_id):
    print(f"\n🔗 LIEN - Analyse {analysis_id}")

    db = get_db()
    urls_data = db.get_urls(analysis_id)

    if not urls_data:
        print("  ℹ  Aucune URL trouvée")
        return {
            "analysis_id": analysis_id,
            "service": "lien",
            "score": 0,
            "url_count": 0,
            "urls_analyzed": [],
            "explanation": "Lien : Aucune URL detectee"
        }

    print(f"  📊 {len(urls_data)} URL(s) trouvée(s)")

    urls_analyzed = []
    url_scores = []
    suspicious_count = 0

    for url_entry in urls_data:
        url = url_entry.get("url", "")
        if not url:
            continue

        analysis = analyze_url(url)
        urls_analyzed.append(analysis)
        url_scores.append(analysis["score"])

        # 🔥 Mise à jour DB : marquer l’URL comme suspecte ou non
        is_suspicious = analysis["score"] >= 50

        db.update_url_suspicious(
            analysis_id,
            analysis["raw_url"],
            is_suspicious
        )

        if is_suspicious:
            suspicious_count += 1

    # Score global = moyenne des scores normalisés
    global_score = round(sum(url_scores) / len(url_scores), 2) if url_scores else 0

    if suspicious_count > 0:
        suspicious_urls = [u["raw_url"] for u in urls_analyzed if u["score"] >= 50]

        if len(suspicious_urls) <= 2:
            url_list = ", ".join(suspicious_urls)
        else:
            url_list = f"{suspicious_urls[0]}, {suspicious_urls[1]} et {len(suspicious_urls)-2} autre(s)"

        explanation = f"Lien : {suspicious_count} URL(s) suspecte(s) ({url_list})"
    else:
        explanation = f"Lien : {len(urls_analyzed)} URL(s) analysee(s), aucune suspecte"

    print(f"  📊 Score global: {global_score}/100")

    return {
        "analysis_id": analysis_id,
        "service": "lien",
        "score": global_score,
        "url_count": len(urls_analyzed),
        "suspicious_count": suspicious_count,
        "urls_analyzed": urls_analyzed,
        "explanation": explanation
    }


@app.route('/')
def home():
    return jsonify({"service": "Lien", "port": 5004})


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
        result = analyze_liens(analysis_id)
        return jsonify(result)
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔗 Lien Service - Port 5004")
    print("Version améliorée avec JSON détaillé")
    print("="*60)

    if GROQ_AVAILABLE:
        print("✅ Groq API: Disponible")
    else:
        print("⚠  Groq API: Non disponible (analyse IA désactivée)")

    print("="*60 + "\n")

    app.run(host="0.0.0.0", port=5004, debug=True)
