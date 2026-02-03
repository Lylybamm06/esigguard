"""
Parser Utils STANDALONE - Version autonome avec database intégré
Port : 5001

MAPPING COMPLET:
===============
Extension Navigateur  →  MySQL Azure
--------------------     ------------
sender.address        →  email_sender        ⭐
subject               →  email_subject       ⭐ CORRIGÉ
body_snippet          →  email_body          ⭐ CORRIGÉ
sender.name           →  display_name
timestamp             →  email_date
urls[]                →  Table urls
attachments[]         →  Table attachments

AUCUNE DÉPENDANCE EXTERNE - TOUT EST DANS CE FICHIER !
"""

from flask import Flask, request, jsonify
from datetime import datetime
import os
import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Optional

# =================================================================
# CLASSE DATABASE INTÉGRÉE
# =================================================================

class PhishingDatabase:
    """Classe pour gérer toutes les interactions avec MySQL Azure"""
    
    def __init__(self):
        self.host = os.getenv('MYSQL_HOST', 'esigguard-mysql.mysql.database.azure.com')
        self.port = int(os.getenv('MYSQL_PORT', '3306'))
        self.database = os.getenv('MYSQL_DATABASE', 'david')
        self.user = os.getenv('MYSQL_USER', 'mysql_admin')
        self.password = os.getenv('MYSQL_PASSWORD', '@Ping632026@')  # ← Plus de mot de passe en dur !

        if not all([self.host, self.database, self.user, self.password]):
            raise ValueError("Variables d'environnement MySQL manquantes")

    def get_connection(self):
        """Établit une connexion à MySQL Azure"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                ssl_disabled=False,
                autocommit=False
            )
            return connection
        except Error as e:
            print(f"❌ Erreur connexion MySQL: {e}")
            raise

    def create_analysis(self, raw_file_path: str) -> int:
        """Crée une nouvelle analyse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO analyses (raw_file_path, upload_date) VALUES (%s, NOW())",
            (raw_file_path,)
        )
        conn.commit()
        analysis_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return analysis_id

    def update_analysis_email_info(self, analysis_id: int, email_data: Dict):
        """Met à jour les infos email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            UPDATE analyses 
            SET email_subject=%s, email_sender=%s, email_date=%s,
                auth_spf=%s, auth_dkim=%s, auth_dmarc=%s,
                display_name=%s, reply_to=%s, return_path=%s,
                sender_ip=%s, sender_country=%s, email_body=%s
            WHERE id=%s
        """
        cursor.execute(query, (
            email_data.get('email_subject'),
            email_data.get('email_sender'),
            email_data.get('email_date'),
            email_data.get('auth_spf'),
            email_data.get('auth_dkim'),
            email_data.get('auth_dmarc'),
            email_data.get('display_name'),
            email_data.get('reply_to'),
            email_data.get('return_path'),
            email_data.get('sender_ip'),
            email_data.get('sender_country'),
            email_data.get('email_body'),
            analysis_id
        ))
        conn.commit()
        cursor.close()
        conn.close()

    def add_urls(self, analysis_id: int, urls: List):
        """Ajoute URLs"""
        if not urls:
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO urls (analysis_id, url, domain, is_suspicious) VALUES (%s, %s, %s, %s)"
        for url_data in urls:
            if isinstance(url_data, str):
                url = url_data
                domain = self._extract_domain(url)
                is_suspicious = False
            else:
                url = url_data.get('url', '')
                domain = url_data.get('domain', '')
                is_suspicious = url_data.get('is_suspicious', False)
            cursor.execute(query, (analysis_id, url, domain, 1 if is_suspicious else 0))
        conn.commit()
        cursor.close()
        conn.close()

    def add_attachments(self, analysis_id: int, attachments: List[Dict]):
        """Ajoute pièces jointes"""
        if not attachments:
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO attachments 
            (analysis_id, filename, file_extension, mime_type, file_size, is_dangerous)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        for att in attachments:
            cursor.execute(query, (
                analysis_id,
                att.get('filename'),
                att.get('extension'),
                att.get('content_type'),
                att.get('size', 0),
                1 if att.get('is_dangerous') else 0
            ))
        conn.commit()
        cursor.close()
        conn.close()

    def _extract_domain(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return ""


def get_db() -> PhishingDatabase:
    """Helper function"""
    return PhishingDatabase()


# =================================================================
# APPLICATION FLASK
# =================================================================

app = Flask(__name__)


# ---------------------------------------------------------
# FONCTION DE PARSING ET STOCKAGE
# ---------------------------------------------------------

def parse_browser_payload():
    """
    Parse le payload navigateur ET stocke dans MySQL
    Retourne: { "success": True, "analysis_id": 42, "parsed_data": {...} }
    """
    raw = request.json or {}

    print("\n" + "="*70)
    print("📧 PARSER NAVIGATEUR - Nouveau email")
    print("="*70)

    # ===== EXTRACTION DES DONNÉES =====
    sender = raw.get("sender", {})
    sender_address = sender.get("address", "")
    display_name   = sender.get("name", "")
    subject        = raw.get("subject", "")          # ✅ Vrais sujet
    body_snippet   = raw.get("body_snippet", "")     # ✅ Corps du texte
    urls           = raw.get("urls", [])
    attachments    = raw.get("attachments", [])
    timestamp_str  = raw.get("timestamp")

    # ===== NETTOYAGE : retirer le subject du body_snippet si présent =====
    if subject and body_snippet:
        # Cas 1 : body commence par le subject exact
        if body_snippet.strip().startswith(subject.strip()):
            body_snippet = body_snippet.strip()[len(subject.strip()):].strip()
        # Cas 2 : séparateurs classiques après le subject (tiret, pipe, deux-points)
        for sep in [" - ", " | ", " : ", "\n", "\t"]:
            if body_snippet.startswith(sep):
                body_snippet = body_snippet[len(sep):].strip()
                break

    print(f"\n📨 Données reçues:")
    print(f"   sender.address  = {sender_address}")
    print(f"   sender.name     = {display_name}")
    print(f"   subject         = {subject}")
    print(f"   body_snippet    = {body_snippet[:80]}..." if body_snippet else "   body_snippet    = (vide)")
    print(f"   urls            = {len(urls)} URL(s)")
    print(f"   attachments     = {len(attachments)} fichier(s)")

    # Domaine expéditeur
    domain = sender_address.split("@")[-1] if "@" in sender_address else ""

    # Normalisation timestamp
    try:
        parsed_ts    = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamp_ms = int(parsed_ts.timestamp() * 1000)
        email_date   = parsed_ts
    except:
        timestamp_ms = None
        email_date   = datetime.now()

    # ===== PRÉPARATION DONNÉES MYSQL =====
    email_data = {
        "email_sender":  sender_address,
        "email_subject": subject,        # ✅ CORRIGÉ : utilise subject
        "email_body":    body_snippet,   # ✅ CORRIGÉ : utilise body_snippet
        "email_date":    email_date,
        "display_name":  display_name,
        "reply_to":      None,
        "return_path":   sender_address,
        "sender_ip":     None,
        "sender_country": None,
        "auth_spf":      "unknown",
        "auth_dkim":     "unknown",
        "auth_dmarc":    "unknown"
    }

    print(f"\n💾 Mapping vers MySQL:")
    print(f"   email_sender  = {email_data['email_sender']}")
    print(f"   email_subject = {email_data['email_subject']}")                       # ✅ Montre le vrais sujet
    print(f"   email_body    = {email_data['email_body'][:80]}..." if email_data['email_body'] else "   email_body    = (vide)")  # ✅ Montre le body
    print(f"   display_name  = {email_data['display_name']}")
    print(f"   email_date    = {email_data['email_date']}")

    # URLs pour table urls
    urls_data = []
    for url in urls:
        url_clean  = url.replace("http://", "").replace("https://", "")
        url_domain = url_clean.split("/")[0]
        urls_data.append({
            "url":          url,
            "domain":       url_domain,
            "is_suspicious": False
        })

    # Attachments pour table attachments
    attachments_data = []
    for att in attachments:
        if isinstance(att, str):
            filename = att
        else:
            filename = att.get("filename", "unknown")

        extension = ""
        if "." in filename:
            extension = "." + filename.split(".")[-1]

        dangerous_ext = [
            # Exécutables
            '.exe', '.msi', '.bat', '.cmd', '.com', '.scr', '.pif',
            '.jar', '.ps1', '.vbs', '.js', '.jse', '.wsf', '.hta',
            # Macros Office
            '.docm', '.xlsm', '.pptm', '.dotm', '.xltm', '.docx',
            # Archives compressées
            '.zip', '.rar', '.7z', '.tar', '.gz', '.iso',
            # Scripts
            '.sh', '.bash', '.py', '.rb', '.php', '.pl',
            # Ambiguës ou détournées
            '.lnk', '.svg', '.rtf', '.eml'
        ]

        is_dangerous = extension.lower() in dangerous_ext

        attachments_data.append({
            "filename":     filename,
            "extension":    extension,
            "content_type": "application/octet-stream",
            "size":         0,
            "is_dangerous": is_dangerous
        })

    # ===== STOCKAGE DANS MYSQL =====
    try:
        db = get_db()
        print("\n💾 Insertion dans MySQL Azure...")

        # 1. Créer l'analyse
        analysis_id = db.create_analysis("Viens du navigateur")
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

        # 5. Mettre le statut à "processing"
        try:
            conn   = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE analyses SET status=%s WHERE id=%s", ("processing", analysis_id))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"   🔄 Statut mis à jour → processing")
        except Exception as e:
            print(f"   ❌ Erreur mise à jour statut: {e}")

        print("\n✅ Stockage MySQL réussi !")
        print("="*70 + "\n")

        parsed = {
            "success":     True,
            "analysis_id": analysis_id,
            "parsed_data": {
                "email_data": {
                    "sender_address": sender_address,
                    "display_name":   display_name,
                    "domain":         domain,
                    "email_subject":  subject,                  # ✅ CORRIGÉ
                    "email_body":     body_snippet,             # ✅ CORRIGÉ
                    "email_sender":   sender_address,
                    "timestamp":      timestamp_ms,
                    "email_date":     email_date.isoformat()
                },
                "urls_count":        len(urls_data),
                "attachments_count": len(attachments_data)
            }
        }
        return parsed

    except Exception as e:
        print(f"\n❌ ERREUR MySQL: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success":    False,
            "error":      str(e),
            "parsed_data": None
        }


# ---------------------------------------------------------
# ROUTES API
# ---------------------------------------------------------

@app.route('/')
def home():
    return jsonify({
        "service": "Parser Navigateur STANDALONE",
        "port":    5001,
        "status":  "running",
        "version": "standalone_with_database",
        "mapping": {
            "sender.address": "email_sender",
            "subject":        "email_subject",   # ✅ CORRIGÉ
            "body_snippet":   "email_body",      # ✅ CORRIGÉ
            "sender.name":    "display_name"
        }
    })


@app.route('/health')
def health():
    try:
        db   = get_db()
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
        "sender":       {"address": "...", "name": "..."},
        "subject":      "...",           ← email_subject
        "body_snippet": "...",           ← email_body
        "urls":         [...],
        "attachments":  [...],
        "timestamp":    "..."
    }

    Réponse:
    {
        "success":     true,
        "analysis_id": 42,
        "parsed_data": {...}
    }
    """
    result = parse_browser_payload()

    if result.get("success"):
        return jsonify(result), 201
    else:
        return jsonify(result), 500


# ---------------------------------------------------------
# LANCEMENT
# ---------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "="*70)
    print("📧 PARSER NAVIGATEUR STANDALONE - Port 5001")
    print("="*70)
    print("\n✨ VERSION AUTONOME - Database intégré")
    print("\n📋 MAPPING:")
    print("   sender.address  → email_sender   ⭐")
    print("   subject         → email_subject  ⭐ CORRIGÉ")
    print("   body_snippet    → email_body     ⭐ CORRIGÉ")
    print("   sender.name     → display_name")
    print("   urls[]          → Table urls")
    print("   attachments[]   → Table attachments")
    print("\n💾 Stockage: MySQL Azure automatique")
    print("\n🔧 Configuration MySQL:")
    print(f"   Host:     {os.getenv('MYSQL_HOST', 'esigguard-mysql.mysql.database.azure.com')}")
    print(f"   Database: {os.getenv('MYSQL_DATABASE', 'david')}")
    print(f"   User:     {os.getenv('MYSQL_USER', 'mysql_admin')}")
    print("="*70 + "\n")

    app.run(host="0.0.0.0", port=5101, debug=True)
