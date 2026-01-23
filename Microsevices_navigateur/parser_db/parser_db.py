from flask import Flask, request, jsonify
import pyodbc
import os
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# =========================================================
# Configuration Azure SQL Database
# =========================================================

class AzureDatabase:
    def __init__(self):
        self.server = os.getenv('AZURE_SQL_SERVER')
        self.database = os.getenv('AZURE_SQL_DATABASE')
        self.username = os.getenv('AZURE_SQL_USERNAME')
        self.password = os.getenv('AZURE_SQL_PASSWORD')
        self.driver = '{ODBC Driver 18 for SQL Server}'
        
    def get_connection(self):
        """Établit une connexion à Azure SQL Database"""
        connection_string = (
            f'DRIVER={self.driver};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            f'UID={self.username};'
            f'PWD={self.password};'
            f'Encrypt=yes;'
            f'TrustServerCertificate=no;'
            f'Connection Timeout=30;'
        )
        return pyodbc.connect(connection_string)
    
    def save_email(self, email_data, attachments_data):
        """Sauvegarde un email et ses pièces jointes dans Azure SQL"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insérer l'email
            insert_email_query = """
            INSERT INTO emails 
            (sender_address, sender_name, domain, subject, body_snippet, 
             urls, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(insert_email_query, (
                email_data.get('sender_address'),
                email_data.get('sender_name'),
                email_data.get('domain'),
                email_data.get('subject'),
                email_data.get('body_snippet'),
                json.dumps(email_data.get('urls', [])),
                email_data.get('timestamp'),
                datetime.utcnow()
            ))
            
            # Récupérer l'ID de l'email inséré
            email_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
            
            # Insérer les pièces jointes
            if attachments_data:
                insert_attachment_query = """
                INSERT INTO attachments 
                (email_id, filename, extension, content_type, size, hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                
                for attachment in attachments_data:
                    cursor.execute(insert_attachment_query, (
                        email_id,
                        attachment.get('filename'),
                        attachment.get('extension'),
                        attachment.get('content_type'),
                        attachment.get('size', 0),
                        attachment.get('hash', ''),
                        datetime.utcnow()
                    ))
                
                print(f"✅ {len(attachments_data)} pièce(s) jointe(s) sauvegardée(s)")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Email sauvegardé dans Azure SQL (ID: {email_id})")
            return email_id
            
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde dans Azure SQL: {str(e)}")
            raise
    
    def get_all_emails(self, limit=10):
        """Récupère les derniers emails avec leurs pièces jointes"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Récupérer les emails
            email_query = """
            SELECT TOP (?) 
                id, sender_address, sender_name, domain, subject, 
                body_snippet, urls, timestamp, created_at
            FROM emails
            ORDER BY created_at DESC
            """
            
            cursor.execute(email_query, limit)
            
            emails = []
            for row in cursor.fetchall():
                email_id = row[0]
                
                # Récupérer les pièces jointes de cet email
                attachment_query = """
                SELECT filename, extension, content_type, size, hash
                FROM attachments
                WHERE email_id = ?
                ORDER BY id
                """
                
                cursor.execute(attachment_query, email_id)
                attachments = []
                for att_row in cursor.fetchall():
                    attachments.append({
                        "filename": att_row[0],
                        "extension": att_row[1],
                        "content_type": att_row[2],
                        "size": att_row[3],
                        "hash": att_row[4]
                    })
                
                emails.append({
                    "id": email_id,
                    "sender_address": row[1],
                    "sender_name": row[2],
                    "domain": row[3],
                    "subject": row[4],
                    "body_snippet": row[5],
                    "urls": json.loads(row[6]) if row[6] else [],
                    "attachments": attachments,
                    "timestamp": row[7],
                    "created_at": row[8].isoformat() if row[8] else None
                })
            
            cursor.close()
            conn.close()
            
            return emails
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération: {str(e)}")
            raise
    
    def get_attachments_stats(self):
        """Récupère les statistiques sur les pièces jointes"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            stats_query = """
            SELECT 
                extension,
                COUNT(*) as count,
                SUM(size) as total_size
            FROM attachments
            WHERE extension IS NOT NULL AND extension != ''
            GROUP BY extension
            ORDER BY count DESC
            """
            
            cursor.execute(stats_query)
            
            stats = []
            for row in cursor.fetchall():
                stats.append({
                    "extension": row[0],
                    "count": row[1],
                    "total_size": row[2] if row[2] else 0
                })
            
            cursor.close()
            conn.close()
            
            return stats
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des stats: {str(e)}")
            raise

# =========================================================
# Fonction pour extraire l'extension d'un fichier
# =========================================================

def get_file_extension(filename):
    """
    Extrait l'extension d'un nom de fichier
    Retourne l'extension en minuscules sans le point
    """
    if not filename:
        return ""
    
    # Utiliser pathlib pour extraire l'extension de manière sûre
    extension = Path(filename).suffix
    
    # Retirer le point et mettre en minuscules
    return extension.lstrip('.').lower() if extension else ""

def parse_attachments(attachments):
    """
    Parse les pièces jointes et extrait les informations pertinentes
    """
    parsed_attachments = []
    
    for attachment in attachments:
        if isinstance(attachment, dict):
            filename = attachment.get('filename', '')
            extension = get_file_extension(filename)
            
            parsed_attachment = {
                'filename': filename,
                'extension': extension,
                'content_type': attachment.get('content_type', ''),
                'size': attachment.get('size', 0),
                'hash': attachment.get('hash', '')
            }
        elif isinstance(attachment, str):
            # Si c'est juste un nom de fichier en string
            filename = attachment
            extension = get_file_extension(filename)
            
            parsed_attachment = {
                'filename': filename,
                'extension': extension,
                'content_type': '',
                'size': 0,
                'hash': ''
            }
        else:
            continue
        
        parsed_attachments.append(parsed_attachment)
    
    return parsed_attachments

# =========================================================
# Fonction de parsing
# =========================================================

def parse_email(payload):
    """
    Parse le payload de l'email et extrait les informations pertinentes
    """
    sender = payload.get("sender", {})
    attachments = payload.get("attachments", [])
    
    # Parser les pièces jointes avec extraction des extensions
    parsed_attachments = parse_attachments(attachments)
    
    email_data = {
        "sender_address": sender.get("address", ""),
        "sender_name": sender.get("name", ""),
        "domain": sender.get("address", "").split("@")[-1] if "@" in sender.get("address", "") else "",
        "subject": payload.get("subject", ""),
        "body_snippet": payload.get("body", "")[:1000],  # Limiter à 1000 caractères
        "urls": payload.get("links", []),
        "timestamp": payload.get("timestamp", datetime.utcnow().isoformat())
    }
    
    return email_data, parsed_attachments

# =========================================================
# Routes Flask
# =========================================================

@app.route('/')
def home():
    """Route racine"""
    return jsonify({
        "status": "running",
        "service": "Email Parser & Azure Storage",
        "version": "2.0",
        "endpoints": {
            "parse": {
                "method": "POST",
                "url": "/parse",
                "description": "Parse un email et l'enregistre dans Azure"
            },
            "emails": {
                "method": "GET",
                "url": "/emails",
                "description": "Récupère les emails stockés (param: limit)"
            },
            "stats": {
                "method": "GET",
                "url": "/stats/attachments",
                "description": "Statistiques sur les pièces jointes"
            },
            "health": {
                "method": "GET",
                "url": "/health",
                "description": "Vérifie la santé du service et la connexion Azure"
            }
        }
    })

@app.route('/health')
def health_check():
    """Vérifie la connexion à Azure"""
    try:
        db = AzureDatabase()
        conn = db.get_connection()
        conn.close()
        return jsonify({
            "status": "healthy",
            "azure_connection": "ok"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "azure_connection": "failed",
            "error": str(e)
        }), 500

@app.route('/emails')
def get_emails():
    """Récupère les emails stockés"""
    try:
        limit = int(request.args.get('limit', 10))
        db = AzureDatabase()
        emails = db.get_all_emails(limit)
        
        return jsonify({
            "total": len(emails),
            "emails": emails
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats/attachments')
def get_attachment_stats():
    """Statistiques sur les pièces jointes"""
    try:
        db = AzureDatabase()
        stats = db.get_attachments_stats()
        
        return jsonify({
            "total_types": len(stats),
            "statistics": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/parse")
def parse_and_store():
    """
    Parse l'email et le sauvegarde dans Azure Database
    """
    try:
        payload = request.json
        
        print("\n===== PARSER : RÉCEPTION EMAIL =====")
        print(f"Expéditeur: {payload.get('sender', {}).get('address', 'N/A')}")
        print(f"Sujet: {payload.get('subject', 'N/A')}")
        
        # Parser l'email
        email_data, attachments_data = parse_email(payload)
        
        # Afficher les pièces jointes parsées
        if attachments_data:
            print(f"\nPièces jointes ({len(attachments_data)}):")
            for att in attachments_data:
                print(f"  - {att['filename']} (extension: .{att['extension']})")
        
        # Sauvegarder dans Azure
        db = AzureDatabase()
        email_id = db.save_email(email_data, attachments_data)
        
        # Préparer la réponse
        result = {
            "email_data": email_data,
            "attachments": attachments_data,
            "azure_email_id": email_id,
            "saved_to_azure": True,
            "attachment_count": len(attachments_data)
        }
        
        print(f"✅ Email parsé et sauvegardé (Azure ID: {email_id})")
        print("=====================================\n")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return jsonify({
            "error": str(e),
            "saved_to_azure": False
        }), 500

# =========================================================
# Lancement du microservice
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
EOF
