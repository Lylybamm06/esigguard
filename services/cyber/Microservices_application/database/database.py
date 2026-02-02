import mysql.connector
from mysql.connector import pooling
from datetime import datetime

class Database:
    def __init__(self):
        self.pool = pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=10,
            host="esigguard-mysql.mysql.database.azure.com",
            user="mysql_admin",
            password="@Ping632026@",
            database="david"
        )

    def get_connection(self):
        return self.pool.get_connection()

    # ---------------------------------------------------------
    # Analyses en attente
    # ---------------------------------------------------------
    def get_pending_analyses(self, limit=100):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM analyses
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    # ---------------------------------------------------------
    # Analyse complète (🔥 corrigée avec attachments + urls)
    # ---------------------------------------------------------
    def get_complete_analysis(self, analysis_id):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1) Analyse principale
        cursor.execute("""
            SELECT *
            FROM analyses
            WHERE id = %s
        """, (analysis_id,))
        row = cursor.fetchone()

        if not row:
            cursor.close()
            conn.close()
            return None

        # 2) Pièces jointes
        cursor.execute("""
            SELECT
                filename,
                file_extension AS extension,
                mime_type,
                file_size AS size,
                is_dangerous
            FROM attachments
            WHERE analysis_id = %s
        """, (analysis_id,))
        attachments = cursor.fetchall()
        row["attachments"] = attachments

        # 3) URLs
        cursor.execute("""
            SELECT
                url,
                domain,
                is_suspicious
            FROM urls
            WHERE analysis_id = %s
        """, (analysis_id,))
        urls = cursor.fetchall()
        row["urls"] = urls

        cursor.close()
        conn.close()
        return row

    # ---------------------------------------------------------
    # Mise à jour infos email
    # ---------------------------------------------------------
    def update_analysis_email_info(self, analysis_id, info):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE analyses SET
                email_subject = %s,
                email_sender = %s,
                email_date = %s,
                display_name = %s,
                reply_to = %s,
                return_path = %s,
                sender_ip = %s,
                sender_country = %s,
                auth_spf = %s,
                auth_dkim = %s,
                auth_dmarc = %s,
                email_body = %s
            WHERE id = %s
        """, (
            info['email_subject'],
            info['email_sender'],
            info['email_date'],
            info['display_name'],
            info['reply_to'],
            info['return_path'],
            info['sender_ip'],
            info['sender_country'],
            info['auth_spf'],
            info['auth_dkim'],
            info['auth_dmarc'],
            info['email_body'],
            analysis_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

    # ---------------------------------------------------------
    # Ajouter pièces jointes
    # ---------------------------------------------------------
    def add_attachments(self, analysis_id, attachments):
        conn = self.get_connection()
        cursor = conn.cursor()

        for att in attachments:
            cursor.execute("""
                INSERT INTO attachments (analysis_id, filename, file_extension, mime_type, file_size, is_dangerous)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                analysis_id,
                att['filename'],
                att['extension'],
                att['content_type'],
                att['size'],
                att['is_dangerous']
            ))

        conn.commit()
        cursor.close()
        conn.close()

    # ---------------------------------------------------------
    # Mise à jour dangerosité pièce jointe
    # ---------------------------------------------------------
    def update_attachment_danger(self, analysis_id, filename, is_dangerous):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE attachments
            SET is_dangerous = %s
            WHERE analysis_id = %s AND filename = %s
        """, (is_dangerous, analysis_id, filename))

        conn.commit()
        cursor.close()
        conn.close()

    # ---------------------------------------------------------
    # Ajouter URLs
    # ---------------------------------------------------------
    def add_urls(self, analysis_id, urls):
        conn = self.get_connection()
        cursor = conn.cursor()

        for u in urls:
            cursor.execute("""
                INSERT INTO urls (analysis_id, url, domain, is_suspicious)
                VALUES (%s, %s, %s, %s)
            """, (
                analysis_id,
                u['url'],
                u['domain'],
                u['is_suspicious']
            ))

        conn.commit()
        cursor.close()
        conn.close()

    # ---------------------------------------------------------
    # Récupérer URLs
    # ---------------------------------------------------------
    def get_urls(self, analysis_id):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT url, domain, is_suspicious
            FROM urls
            WHERE analysis_id = %s
        """, (analysis_id,))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    # ---------------------------------------------------------
    # Mise à jour is_suspicious pour une URL
    # ---------------------------------------------------------
    def update_url_suspicious(self, analysis_id, url, is_suspicious):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE urls
            SET is_suspicious = %s
            WHERE analysis_id = %s AND url = %s
        """, (is_suspicious, analysis_id, url))

        conn.commit()
        cursor.close()
        conn.close()

    # ---------------------------------------------------------
    # Mise à jour statut analyse
    # ---------------------------------------------------------
    def update_status(self, analysis_id, new_status):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE analyses
            SET status = %s
            WHERE id = %s
        """, (new_status, analysis_id))

        conn.commit()
        cursor.close()
        conn.close()

    # ---------------------------------------------------------
    # Mise à jour résultats cyber
    # ---------------------------------------------------------
    def update_cyber_results(self, analysis_id, explanation, score):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE analyses
            SET explanation_cyber = %s,
                score_cyber = %s
            WHERE id = %s
        """, (explanation, score, analysis_id))

        conn.commit()
        cursor.close()
        conn.close()

    # ---------------------------------------------------------
    # Mise à jour pays d'origine IP
    # ---------------------------------------------------------
    def update_sender_country(self, analysis_id, ip, country):
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
           UPDATE analyses
           SET sender_country = %s
           WHERE id = %s
        """

        cursor.execute(query, (country, analysis_id))
        conn.commit()

        cursor.close()
        conn.close()


# Singleton
_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
