"""
Parser Utils STANDALONE - Version autonome avec database intégré
Port : 5001
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
        self.database = os.getenv('MYSQL_DATABASE', 'esigguard_data')
        self.user = os.getenv('MYSQL_USER', 'mysql_admin')
        self.password = os.getenv('MYSQL_PASSWORD', '@Ping632026@')

        if not all([self.host, self.database, self.user, self.password]):
            raise ValueError("Variables d'environnement MySQL manquantes")

    def get_connection(self):
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
        if not urls:
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO urls (analysis_id, url, domain, is_suspicious) VALUES (%s, %s, %s, %s)"
        for url_data in urls:
            url = url_data.get('url', '')
            domain = url_data.get('domain', '')
            is_suspicious = url_data.get('is_suspicious', False)
            cursor.execute(query, (analysis_id, url, domain, 1 if is_suspicious else 0))
        conn.commit()
        cursor.close()
        conn.close()

    def add_attachments(self, analysis_id: int, attachments: List[Dict]):
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
                att.get('filename'),
                att.get('extension'),
                att.get('content_type'),
                att.get('size', 0),
                1 if att.get('is_dangerous') else 0
            ))
        conn.commit()
        cursor.close()
        conn.close()


def get_db() -> PhishingDatabase:
    return PhishingDatabase()


# =================================================================
# APPLICATION FLASK
# =================================================================

app = Flask(__name__)


# ---------------------------------------------------------
# FONCTION DE PARSING ET STOCKAGE
# ---------------------------------------------------------

def parse_browser_payload():
    raw = request.json or {}

    print("\n" + "="*70)
    print("📧 PARSER NAVIGATEUR - Nouveau email")
    print("="*70)

    sender = raw.get("sender", {})
    sender_address = sender.get("address", "")
    display_name   = sender.get("name", "")
    subject        = raw.get("subject", "")
    body_snippet   = raw.get("body_snippet", "")
    urls           = raw.get("urls", [])
    attachments    = raw.get("attachments", [])
    timestamp_str  = raw.get("timestamp")

    # 🔥 DÉDUPLICATION + NETTOYAGE DES URLS
    clean_urls = []
    seen = set()

    for url in urls:
        if not isinstance(url, str):
            continue

        normalized = url.strip().lower()

        if "@" in normalized and not normalized.startswith("http"):
            continue

        if normalized.startswith("mailto:"):
            continue

        if len(normalized) < 8:
            continue

        if normalized not in seen:
            seen.add(normalized)
            clean_urls.append(url)

    # Construction des URLs propres
    urls_data = []
    for url in clean_urls:
        url_clean  = url.replace("http://", "").replace("https://", "")
        url_domain = url_clean.split("/")[0]
        urls_data.append({
            "url":          url,
            "domain":       url_domain,
            "is_suspicious": False
        })

    # Nettoyage du body
    if subject and body_snippet:
        if body_snippet.strip().startswith(subject.strip()):
            body_snippet = body_snippet.strip()[len(subject.strip()):].strip()

    # Normalisation timestamp
    try:
        parsed_ts    = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamp_ms = int(parsed_ts.timestamp() * 1000)
        email_date   = parsed_ts
    except:
        timestamp_ms = None
        email_date   = datetime.now()

    email_data = {
        "email_sender":  sender_address,
        "email_subject": subject,
        "email_body":    body_snippet,
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

    # Stockage MySQL
    try:
        db = get_db()

        analysis_id = db.create_analysis("Viens du navigateur")
        db.update_analysis_email_info(analysis_id, email_data)

        if urls_data:
            db.add_urls(analysis_id, urls_data)

        # Attachments
        attachments_data = []
        for att in attachments:
            filename = att.get("filename", "unknown") if isinstance(att, dict) else att
            extension = "." + filename.split(".")[-1] if "." in filename else ""
            attachments_data.append({
                "filename": filename,
                "extension": extension,
                "content_type": "application/octet-stream",
                "size": 0,
                "is_dangerous": extension.lower() in [
                    '.exe','.msi','.bat','.cmd','.com','.scr','.pif','.jar','.ps1','.vbs','.js','.jse','.wsf','.hta',
                    '.docm','.xlsm','.pptm','.dotm','.xltm','.docx','.zip','.rar','.7z','.tar','.gz','.iso',
                    '.sh','.bash','.py','.rb','.php','.pl','.lnk','.svg','.rtf','.eml'
                ]
            })

        if attachments_data:
            db.add_attachments(analysis_id, attachments_data)

        # Statut
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE analyses SET status=%s WHERE id=%s", ("processing", analysis_id))
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "success": True,
            "analysis_id": analysis_id,
            "parsed_data": {
                "email_data": {
                    "sender_address": sender_address,
                    "display_name":   display_name,
                    "domain":         sender_address.split("@")[-1],
                    "email_subject":  subject,
                    "email_body":     body_snippet,
                    "email_sender":   sender_address,
                    "timestamp":      timestamp_ms,
                    "email_date":     email_date.isoformat()
                },
                "urls_count": len(urls_data),
                "attachments_count": len(attachments_data)
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------
# ROUTES API
# ---------------------------------------------------------

@app.post("/parse")
def parse_only():
    result = parse_browser_payload()
    return jsonify(result), (201 if result.get("success") else 500)


# ---------------------------------------------------------
# LANCEMENT
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5101, debug=True)
