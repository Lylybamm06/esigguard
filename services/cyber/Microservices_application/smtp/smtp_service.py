"""
SMTP Service - Version améliorée avec JSON détaillé
Port : 5007
"""

from flask import Flask, jsonify
import os, sys, requests, re

sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)

def check_ip_reputation(ip):
    """Vérifie réputation IP via VirusTotal"""
    api_key = os.getenv("VT_API_KEY")
    if not api_key or api_key == "votre_cle_virustotal":
        return {
            "ip": ip,
            "status": "unknown",
            "malicious_reports": 0
        }
    
    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
    headers = {"x-apikey": api_key}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            
            return {
                "ip": ip,
                "status": "not reliable" if malicious > 0 else "reliable",
                "malicious_reports": malicious
            }
        else:
            return {
                "ip": ip,
                "status": "unknown",
                "malicious_reports": 0
            }
    except Exception as e:
        print(f"⚠️  Erreur VirusTotal IP: {e}")
        return {
            "ip": ip,
            "status": "unknown",
            "malicious_reports": 0
        }

def get_ip_geolocation(ip):
    """Géolocalise IP via ip2location"""
    api_key = os.getenv("IP2LOC_API_KEY")
    if not api_key or api_key == "votre_cle_ip2location":
        return {
            "ip": ip,
            "country": "Unknown",
            "region": "Unknown",
            "city": "Unknown"
        }
    
    url = f"https://api.ip2location.io/?key={api_key}&ip={ip}&format=json"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "ip": ip,
                "country": data.get("country_name", "Unknown"),
                "region": data.get("region_name", "Unknown"),
                "city": data.get("city_name", "Unknown")
            }
        else:
            return {
                "ip": ip,
                "country": "Unknown",
                "region": "Unknown",
                "city": "Unknown"
            }
    except Exception as e:
        print(f"⚠️  Erreur Géolocalisation: {e}")
        return {
            "ip": ip,
            "country": "Unknown",
            "region": "Unknown",
            "city": "Unknown"
        }

def analyze_headers(analysis):
    """Analyse des en-têtes SMTP"""
    # Vérifier présence Message-ID
    # Note: Cette info n'est pas extraite par le parser actuel
    # On pourrait l'ajouter mais pour l'instant on met "unknown"
    message_id_present = "unknown"
    
    # Vérifier List-Unsubscribe
    list_unsubscribe_present = "unknown"
    
    # Analyse timestamp (email_date présent ?)
    email_date = analysis.get("email_date")
    timestamp_status = "ok" if email_date else "missing"
    
    # Headers status
    headers_status = "normal"
    
    return {
        "timestamp_status": timestamp_status,
        "message_id_present": message_id_present,
        "list_unsubscribe_present": list_unsubscribe_present,
        "headers_status": headers_status
    }

def calculate_smtp_score(ip_reputation, ip_geolocation, headers):
    """Calcule le score SMTP"""
    score = 0
    reasons = []
    
    # IP Reputation (+40 si malicious)
    if ip_reputation.get("status") == "not reliable":
        score += 40
        reasons.append(f"IP malveillante ({ip_reputation.get('malicious_reports')} signalements)")
    elif ip_reputation.get("status") == "unknown":
        score += 15
        reasons.append("Réputation IP inconnue")
    
    # Géolocalisation suspecte (+20 si pays à risque)
    # Pour simplifier, on n'ajoute pas de points ici
    # Mais on pourrait vérifier si country est dans une liste noire
    
    # List-Unsubscribe absent ou inconnu (+10)
    list_unsub = headers.get("list_unsubscribe_present")
    if list_unsub in ["no", "unknown"]:
        score += 10
        reasons.append("Pas de lien de desinscription")
    
    # Timestamp manquant (+15)
    if headers.get("timestamp_status") == "missing":
        score += 15
        reasons.append("Timestamp manquant")
    
    return min(100, score), reasons

def analyze_smtp(analysis_id):
    """Analyse SMTP complète"""
    print(f"\n📧 SMTP - Analyse {analysis_id}")
    
    db = get_db()
    analysis = db.get_complete_analysis(analysis_id)
    
    if not analysis:
        raise ValueError(f"Analyse {analysis_id} introuvable")
    
    # Récupérer IP source
    origin_ip = analysis.get('sender_ip')
    
    if not origin_ip:
        print("  ⚠️  Pas d'IP source identifiée")
        
        return {
            "analysis_id": analysis_id,
            "service": "smtp",
            "score": 30,
            "origin_ip": None,
            "ip_reputation": {
                "ip": None,
                "status": "unknown",
                "malicious_reports": 0
            },
            "ip_geolocation": {
                "ip": None,
                "country": "Unknown",
                "region": "Unknown",
                "city": "Unknown"
            },
            "timestamp_status": "ok",
            "message_id_present": "unknown",
            "list_unsubscribe_present": "unknown",
            "headers_status": "normal",
            "explanation": "SMTP : IP source non identifiee"
        }
    
    print(f"  🔍 IP source: {origin_ip}")
    
    # Analyses
    ip_reputation = check_ip_reputation(origin_ip)
    ip_geolocation = get_ip_geolocation(origin_ip)
    headers = analyze_headers(analysis)
    
    print(f"  📍 Localisation: {ip_geolocation.get('city')}, {ip_geolocation.get('country')}")
    print(f"  🛡️  Réputation: {ip_reputation.get('status')}")
    
    # Mise à jour MySQL (sender_country)
    country = ip_geolocation.get("country", "Unknown")
    try:
        db.update_sender_country(analysis_id, origin_ip, country)
        print(f"  💾 MySQL mis à jour: country={country}")
    except Exception as e:
        print(f"  ⚠️  Erreur mise à jour MySQL: {e}")
    
    # Calcul score
    score, reasons = calculate_smtp_score(ip_reputation, ip_geolocation, headers)
    
    # Explication
    if reasons:
        explanation = f"SMTP : {', '.join(reasons)}"
    else:
        explanation = f"SMTP : IP identifiee ({origin_ip}, {country}), aucun indicateur suspect"
    
    print(f"  📊 Score: {score}/100")
    
    return {
        "analysis_id": analysis_id,
        "service": "smtp",
        "score": score,
        "origin_ip": origin_ip,
        "ip_reputation": ip_reputation,
        "ip_geolocation": ip_geolocation,
        "timestamp_status": headers["timestamp_status"],
        "message_id_present": headers["message_id_present"],
        "list_unsubscribe_present": headers["list_unsubscribe_present"],
        "headers_status": headers["headers_status"],
        "explanation": explanation
    }

@app.route('/')
def home():
    return jsonify({"service": "SMTP", "port": 5007})

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
        result = analyze_smtp(analysis_id)
        return jsonify(result)
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "="*60)
    print("📧 SMTP Service - Port 5007")
    print("Version améliorée avec JSON détaillé")
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=5007, debug=True)
