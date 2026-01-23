import os
import time
import json
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        database=os.getenv('DB_NAME')
    )

def run_module(script_path, output_json):
    print(f"   > Exécution {script_path}...")
    os.system(f"python3 {script_path}")
    json_path = os.path.join("/results", output_json)
    try:
        with open(json_path, 'r') as f: return json.load(f)
    except: return {}

def process_job(job):
    job_id = job['id']
    file_path = job['raw_file_path']
    print(f"--- Job {job_id} : {file_path} ---")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE analyses SET status='processing_cyber' WHERE id=%s", (job_id,))
    conn.commit()

    os.environ['EMAIL_FILE'] = os.path.basename(file_path)

    # 1. AUTH
    auth = run_module("auth/auth.py", "auth.json")
    if auth:
        cursor.execute("UPDATE analyses SET auth_spf=%s, auth_dkim=%s, score_cyber=%s WHERE id=%s", 
                       (auth.get('spf'), auth.get('dkim'), int(auth.get('score', 0)), job_id))

    # 2. SMTP
    smtp = run_module("smtp/smtp.py", "smtp.json")
    if smtp:
        geo = smtp.get('geolocation', {})
        cursor.execute("UPDATE analyses SET sender_ip=%s, sender_country=%s WHERE id=%s", 
                       (smtp.get('source_ip'), geo.get('country'), job_id))

    # 3. CONTENT
    content = run_module("content/content.py", "content.json")
    if content:
        verdict = content.get('content', {}).get('ai_content_analysis', {}).get('global_verdict', 'unknown')
        cursor.execute("UPDATE analyses SET explanation_cyber=%s WHERE id=%s", (verdict, job_id))

    # 4. FILES
    files = run_module("file/file.py", "files.json")
    if files:
        cursor.execute("UPDATE analyses SET attachments_count=%s WHERE id=%s", (files.get('attachment_count', 0), job_id))

    # Fin
    cursor.execute("UPDATE analyses SET status='cyber_done' WHERE id=%s", (job_id,))
    conn.commit()
    conn.close()

def main_loop():
    print("Worker DB démarré.")
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM analyses WHERE status='pending' LIMIT 1")
            job = cursor.fetchone()
            conn.close()
            if job: process_job(job)
            else: time.sleep(2)
        except Exception as e:
            print(f"Erreur: {e}")
            time.sleep(5)

if __name__ == "__main__":
    time.sleep(5)
    main_loop()