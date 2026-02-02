from flask import Flask, jsonify, request
import json
import os
import requests
from datetime import datetime, UTC
from pathlib import Path
from groq import Groq
from groq import RateLimitError  # ← Import spécifique pour catcher l'erreur 429

print("🔥🔥🔥 LIEN.PY CHARGÉ (VERSION OPTIMISÉE - MAX 8 LIENS GROQ) 🔥🔥🔥")

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
    print(f"\n🔍 [REPUTATION] Vérification de : {domain}")
    try:
        api_key = os.getenv("VT_API_KEY")
        url = f"https://www.virustotal.com/api/v3/domains/{domain}"
        headers = {"x-apikey": api_key}

        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            data = r.json()
            malicious = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {}).get("malicious", 0)
            status = "reliable" if malicious == 0 else "not reliable"

            result = {
                "domain": domain,
                "status": status,
                "malicious_reports": malicious
            }
            print(f"✅ [REPUTATION] Résultat : {result}")
            return result

    except Exception as e:
        print(f"❌ [REPUTATION] Erreur : {str(e)}")
        return {"domain": domain, "status": "unknown", "error": str(e)}

    print(f"⚠️ [REPUTATION] Statut unknown par défaut")
    return {"domain": domain, "status": "unknown"}

# ---------------------------------------------------------
# Vérification âge du domaine via WHOIS
# ---------------------------------------------------------

def get_domain_age(domain):
    print(f"\n🔍 [DOMAIN_AGE] Vérification de : {domain}")
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

                result = {
                    "created": created_date,
                    "age_years": round(age_years, 2),
                    "status": status
                }
                print(f"✅ [DOMAIN_AGE] Résultat : {result}")
                return result
        else:
            print(f"⚠️ [DOMAIN_AGE] Pas de clé API WHOIS")
    except Exception as e:
        print(f"❌ [DOMAIN_AGE] Erreur : {str(e)}")
    
    print(f"⚠️ [DOMAIN_AGE] Statut unknown par défaut")
    return {"status": "unknown"}

# ---------------------------------------------------------
# Analyse IA du lien via Groq (avec gestion rate limit)
# ---------------------------------------------------------

def ai_analyze_link(display_text, raw_url, domain):
    print(f"\n🔍 [AI_ANALYSIS] Analyse de : {domain}")
    
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

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        result = json.loads(raw)
        print(f"✅ [AI_ANALYSIS] Résultat : {result}")
        return result
    
    except RateLimitError as e:
        # Gestion spécifique du rate limit Groq (429)
        print(f"⚠️ [AI_ANALYSIS] Rate limit Groq atteint (429)")
        print(f"   Détails : {str(e)}")
        return {
            "status": "unknown",
            "reason": "Analyse IA non disponible (quota API Groq épuisé)"
        }
        
    except Exception as e:
        # Autres erreurs (parsing JSON, réseau, etc.)
        error_msg = str(e)
        print(f"❌ [AI_ANALYSIS] Erreur : {error_msg}")
        return {
            "status": "unknown",
            "reason": f"Erreur lors de l'analyse : {error_msg}"
        }

# ---------------------------------------------------------
# Calcul du score pour un lien (NOUVEAU : sur 100)
# ---------------------------------------------------------

def calculate_link_score(reputation, domain_age, ai_analysis):
    print(f"\n{'='*60}")
    print(f"🎯 DÉBUT CALCUL SCORE")
    print(f"{'='*60}")
    
    MAX_SCORE = 100  # ← Changé de 130 à 100
    score = 0
    
    print(f"\n📥 Données reçues :")
    print(f"   reputation  : {reputation}")
    print(f"   domain_age  : {domain_age}")
    print(f"   ai_analysis : {ai_analysis}")
    print(f"\n💯 Score initial : {score}")

    # Réputation (40 points)
    print(f"\n🔍 Test 1 : Réputation")
    rep_status = reputation.get("status")
    print(f"   reputation.get('status') = '{rep_status}'")
    print(f"   Test : '{rep_status}' == 'not reliable' ? {rep_status == 'not reliable'}")
    
    if reputation.get("status") == "not reliable":
        score += 40  # ← Changé de 50 à 40
        print(f"   ✅ AJOUT +40 → score = {score}")
    else:
        print(f"   ❌ Pas de pénalité")

    # Âge du domaine (40 points)
    print(f"\n🔍 Test 2 : Âge du domaine")
    age_status = domain_age.get("status")
    print(f"   domain_age.get('status') = '{age_status}'")
    print(f"   Type : {type(age_status)}")
    print(f"   Test suspect : '{age_status}' == 'suspect' ? {age_status == 'suspect'}")
    print(f"   Test unknown : '{age_status}' == 'unknown' ? {age_status == 'unknown'}")
    
    if age_status == "suspect":
        score += 40  # ← Changé de 50 à 40
        print(f"   ✅ SUSPECT → AJOUT +40 → score = {score}")
    elif age_status == "unknown":
        score += 40  # ← Changé de 50 à 40
        print(f"   ✅ UNKNOWN → AJOUT +40 → score = {score}")
    else:
        print(f"   ❌ BON ou autre → Pas de pénalité")

    # Analyse IA (20 points)
    print(f"\n🔍 Test 3 : Analyse IA")
    ai_status = ai_analysis.get("status")
    print(f"   ai_analysis.get('status') = '{ai_status}'")
    
    if ai_status == "skipped":
        print(f"   ⏭️ SKIPPED → Pas d'analyse IA (trop de liens)")
    elif ai_status == "suspect":
        score += 20  # ← Changé de 30 à 20
        print(f"   ✅ SUSPECT → AJOUT +20 → score = {score}")
    else:
        print(f"   ❌ Pas de pénalité")

    # Percentage = score directement (car MAX = 100)
    percentage = score
    
    print(f"\n{'='*60}")
    print(f"✅ SCORE FINAL = {score} / {MAX_SCORE} ({percentage}%)")
    print(f"{'='*60}\n")

    return score, percentage

# ---------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------

def check_links(parsed_email):
    print(f"\n{'#'*60}")
    print(f"🚀 DÉBUT ANALYSE DES LIENS")
    print(f"{'#'*60}")

    links = parsed_email["email_data"].get("urls", [])
    nb_links = len(links)
    
    print(f"\n📊 Nombre de liens trouvés : {nb_links}")
    print(f"   Liens : {links}")
    
    # 🆕 Désactiver Groq si > 8 liens (pour économiser le quota API)
    use_groq = nb_links <= 8
    
    if not use_groq:
        print(f"\n⚠️ GROQ DÉSACTIVÉ : {nb_links} liens détectés (> 8)")
        print(f"   → Analyse basée uniquement sur VirusTotal + WHOIS\n")
    else:
        print(f"\n✅ GROQ ACTIVÉ : {nb_links} liens (≤ 8)\n")
    
    results = []
    total_score = 0

    for i, raw_url in enumerate(links, 1):
        print(f"\n{'─'*60}")
        print(f"🔗 LIEN {i}/{nb_links} : {raw_url}")
        print(f"{'─'*60}")
        
        raw_url = clean_url(raw_url)
        display_text = raw_url
        domain = raw_url.replace("http://", "").replace("https://", "").split("/")[0]
        
        print(f"   URL nettoyée : {raw_url}")
        print(f"   Domaine extrait : {domain}")

        # Collecte des analyses
        reputation = check_domain_reputation(domain)
        age_info = get_domain_age(domain)
        
        # 🆕 Analyse IA uniquement si ≤ 8 liens
        if use_groq:
            ai_report = ai_analyze_link(display_text, raw_url, domain)
        else:
            ai_report = {
                "status": "skipped",
                "reason": f"Analyse IA désactivée ({nb_links} liens > 8)"
            }
            print(f"\n⏭️ [AI_ANALYSIS] Skippée (trop de liens)")

        # Calcul du score
        link_score, link_percentage = calculate_link_score(reputation, age_info, ai_report)
        total_score += link_score
        
        print(f"\n📊 Résultat pour ce lien :")
        print(f"   link_score = {link_score}")
        print(f"   link_percentage = {link_percentage}")
        print(f"   is_suspicious = {link_score > 0}")

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

    # nb_links déjà défini au début de la fonction
    average_score = round(total_score / nb_links, 2) if nb_links > 0 else 0
    global_percentage = average_score  # Simplifié car MAX = 100

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

    print(f"\n{'#'*60}")
    print(f"📊 RÉSUMÉ GLOBAL")
    print(f"{'#'*60}")
    print(f"   Total liens : {nb_links}")
    print(f"   Total score : {total_score}")
    print(f"   Score moyen : {average_score}")
    print(f"   Pourcentage : {global_percentage}%")
    print(f"   Niveau risque : {risk_level}")
    print(f"   Liens suspects : {len(suspect_links)}")
    print(f"{'#'*60}\n")

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
    print(f"\n🌐 ===== NOUVELLE REQUÊTE REÇUE =====\n")

    try:
        parsed = request.get_json(force=True)
        result = check_links(parsed)

        filename = LINK_STORAGE / f"lien_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "parsed_email": parsed,
                "links_analysis": result,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

        print(f"💾 [LIEN] Analyse sauvegardée dans : {filename}\n")

        return jsonify(result)
    
    except Exception as e:
        # Gestion d'erreur globale : ne fait pas crasher le service
        error_msg = str(e)
        print(f"\n❌ [ERROR] Erreur critique dans analyze_links :")
        print(f"   {error_msg}\n")
        
        # Retourner une réponse d'erreur au lieu de crasher
        return jsonify({
            "error": True,
            "message": "Erreur lors de l'analyse des liens",
            "details": error_msg,
            "links_analysis": [],
            "nb_links": 0,
            "score": 0,
            "percentage": 0,
            "risk_level": "unknown",
            "explanation": "Erreur lors de l'analyse"
        }), 500

# ---------------------------------------------------------
# Lancement du microservice
# ---------------------------------------------------------

if __name__ == "__main__":
    print("\n🚀 Démarrage du serveur Flask sur http://0.0.0.0:5105")
    print("📝 Mode DEBUG activé - tous les détails seront affichés")
    print("✅ Gestion rate limit Groq activée")
    print("✅ Scoring sur 100 (intuitif)")
    print("⚡ Groq désactivé si > 8 liens (économie de quota)\n")
    app.run(host="0.0.0.0", port=5105)
