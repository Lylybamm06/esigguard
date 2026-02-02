"""
Parser Utils - Parse les emails du navigateur et stocke dans MySQL Azure
Port : 5009

MAPPING COMPLET:
===============
Extension Navigateur    →  MySQL Azure
--------------------       ------------
sender.address          →  email_sender      ⭐
body_snippet            →  email_subject     ⭐
sender.name             →  display_name
timestamp               →  email_date
urls[]                  →  Table urls
attachments[]           →  Table attachments
"""

from flask import Flask, request, jsonify
from datetime import datetime
import os
import sys

# Importer le module database
sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)

# ---------------------------------------------------------
# FONCTION DE PARSING ET STOCKAGE
# ---------------------------------------------------------

def parse_browser_payload():
    """
    Parse le payload navigateur ET stocke dans MySQL
    
    Retourne:
    {
      "success": True,
      "analysis_id": 42,
      "parsed_data": {...}
    }
    """
    
    raw = request.json or {}
    
    print("\n" + "="*70)
    print("📧 PARSER NAVIGATEUR - Nouveau email")
    print("="*70)
    
    # ===== EXTRACTION DES DONNÉES =====
    
    sender = raw.get("sender", {})
    sender_address = sender.get("address", "")
    display_name = sender.get("name", "")
    
    subject = raw.get("subject", "")              # Non utilisé
    body_snippet = raw.get("body_snippet", "")    # ⭐ Devient email_subject
    urls = raw.get("urls", [])
    attachments = raw.get("attachments", [])
    timestamp_str = raw.get("timestamp")
    
    print(f"\n📨 Données reçues:")
    print(f"   sender.address    = {sender_address}")
    print(f"   sender.name       = {display_name}")
    print(f"   subject           = {subject} (ignoré)")
    print(f"   body_snippet      = {body_snippet[:50]}...")
    print(f"   urls              = {len(urls)} URL(s)")
    print(f"   attachments       = {len(attachments)} fichier(s)")
    
    # Domaine expéditeur
    domain = sender_address.split("@")[-1] if "@" in sender_address else ""
    
    # Normalisation timestamp
    try:
        parsed_ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamp_ms = int(parsed_ts.timestamp() * 1000)
        email_date = parsed_ts
    except:
        timestamp_ms = None
        email_date = datetime.now()
    
    # ===== PRÉPARATION DONNÉES MYSQL =====
    
    # Données pour table analyses
    email_data = {
        "email_sender": sender_address,      # ⭐ sender.address → email_sender
        "email_subject": body_snippet,       # ⭐ body_snippet → email_subject
        "email_body": body_snippet,          # body_snippet → email_body aussi
        "email_date": email_date,
        "display_name": display_name,        # sender.name → display_name
        "reply_to": None,
        "return_path": sender_address,
        "sender_ip": None,
        "sender_country": None,
        "auth_spf": "unknown",
        "auth_dkim": "unknown",
        "auth_dmarc": "unknown"
    }
    
    print(f"\n💾 Mapping vers MySQL:")
    print(f"   email_sender      = {email_data['email_sender']}")
    print(f"   email_subject     = {email_data['email_subject'][:50]}...")
    print(f"   display_name      = {email_data['display_name']}")
    print(f"   email_date        = {email_data['email_date']}")
    
    # URLs pour table urls
    urls_data = []
    for url in urls:
        # Extraire domaine
        url_clean = url.replace("http://", "").replace("https://", "")
        url_domain = url_clean.split("/")[0]
        
        urls_data.append({
            "url": url,
            "domain": url_domain,
            "is_suspicious": False
        })
    
    # Attachments pour table attachments
    attachments_data = []
    for att in attachments:
        if isinstance(att, str):
            filename = att
        else:
            filename = att.get("filename", "unknown")
        
        # Extraire extension
        extension = ""
        if "." in filename:
            extension = "." + filename.split(".")[-1]
        
        # Extensions dangereuses
        dangerous_ext = ['.exe', '.bat', '.vbs', '.js', '.scr', '.cmd', '.com', '.pif']
        is_dangerous = extension.lower() in dangerous_ext
        
        attachments_data.append({
            "filename": filename,
            "extension": extension,
            "content_type": "application/octet-stream",
            "size": 0,
            "is_dangerous": is_dangerous
        })
    
    # ===== STOCKAGE DANS MYSQL =====
    
    try:
        db = get_db()
        
        print("\n💾 Insertion dans MySQL Azure...")
        
        # 1. Créer l'analyse
        analysis_id = db.create_analysis("/tmp/navigateur_email.json")
        print(f"   ✅ Analyse créée: ID = {analysis_id}")
        
        # 2. Mettre à jour avec les données email
        db.update_analysis_email_info(analysis_id, email_data)
        print(f"   ✅ Données email mises à jour")
        
        # 3. Ajouter URLs
        if urls_data:
            db.add_urls(analysis_id, urls_data)
            print(f"   ✅ {len(urls_data)} URL(s) ajoutée(s)")
        
        # 4. Ajouter attachments
        if attachments_data:
            db.add_attachments(analysis_id, attachments_data)
            print(f"   ✅ {len(attachments_data)} pièce(s) jointe(s) ajoutée(s)")
        
        print("\n✅ Stockage MySQL réussi !")
        print("="*70 + "\n")
        
        # Résultat
        parsed = {
            "success": True,
            "analysis_id": analysis_id,
            "parsed_data": {
                "email_data": {
                    "sender_address": sender_address,
                    "display_name": display_name,
                    "domain": domain,
                    "email_subject": body_snippet,      # ⭐ body_snippet stocké ici
                    "email_sender": sender_address,     # ⭐ sender.address stocké ici
                    "timestamp": timestamp_ms,
                    "email_date": email_date.isoformat()
                },
                "urls_count": len(urls_data),
                "attachments_count": len(attachments_data)
            }
        }
        
        return parsed
        
    except Exception as e:
        print(f"\n❌ ERREUR MySQL: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "parsed_data": None
        }

# ---------------------------------------------------------
# ROUTES API
# ---------------------------------------------------------

@app.route('/')
def home():
    return jsonify({
        "service": "Parser Navigateur",
        "port": 5009,
        "status": "running",
        "mapping": {
            "sender.address": "email_sender",
            "body_snippet": "email_subject",
            "sender.name": "display_name"
        }
    })

@app.route('/health')
def health():
    try:
        db = get_db()
        conn = db.get_connection()
        conn.close()
        return jsonify({"status": "healthy"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.post("/parse")
def parse_only():
    """
    Parse le payload navigateur et stocke dans MySQL
    
    Requête:
    {
      "sender": {"address": "...", "name": "..."},
      "subject": "...",
      "body_snippet": "...",
      "urls": [...],
      "attachments": [...],
      "timestamp": "..."
    }
    
    Réponse:
    {
      "success": true,
      "analysis_id": 42,
      "parsed_data": {...}
    }
    """
    
    result = parse_browser_payload()
    
    if result.get("success"):
        return jsonify(result), 201  # 201 Created
    else:
        return jsonify(result), 500  # 500 Internal Server Error

# ---------------------------------------------------------
# LANCEMENT
# ---------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "="*70)
    print("📧 PARSER NAVIGATEUR - Port 5009")
    print("="*70)
    print("\n📋 MAPPING:")
    print("   sender.address  →  email_sender   ⭐")
    print("   body_snippet    →  email_subject  ⭐")
    print("   sender.name     →  display_name")
    print("   urls[]          →  Table urls")
    print("   attachments[]   →  Table attachments")
    print("\n💾 Stockage: MySQL Azure automatique")
    print("="*70 + "\n")
    
    app.run(host="0.0.0.0", port=5009, debug=True)
