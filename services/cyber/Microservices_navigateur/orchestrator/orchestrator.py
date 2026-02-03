from flask import Flask, request, jsonify
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import mysql.connector


app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response



class DB:
    def __init__(self):
        self.host = "esigguard-mysql.mysql.database.azure.com"
        self.port = 3306
        self.database = "esigguard_data"
        self.user = "mysql_admin"
        self.password = "@Ping632026@"

    def connect(self):
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            ssl_disabled=False,
            autocommit=True
        )

    def update_cyber_results(self, analysis_id, explanation, score):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE analyses
            SET score_cyber=%s, explanation_cyber=%s
            WHERE id=%s
        """, (score, explanation, analysis_id))
        cursor.close()
        conn.close()

    def update_status(self, analysis_id, status):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE analyses
            SET status=%s
            WHERE id=%s
        """, (status, analysis_id))
        cursor.close()
        conn.close()

    def insert_url_if_missing(self, analysis_id, url):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM urls WHERE analysis_id=%s AND url=%s
        """, (analysis_id, url))
        exists = cursor.fetchone()[0]

        if not exists:
            cursor.execute("""
                INSERT INTO urls (analysis_id, url, is_suspicious)
                VALUES (%s, %s, NULL)
            """, (analysis_id, url))

        cursor.close()
        conn.close()

    def update_url_suspicion(self, analysis_id, url, is_suspicious):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE urls
            SET is_suspicious=%s
            WHERE analysis_id=%s AND url=%s
        """, (1 if is_suspicious else 0, analysis_id, url))
        cursor.close()
        conn.close()


db = DB()


STORAGE_DIR = Path("./storage")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

PARSER_URL = "http://parser:5101/parse"

SERVICES = {
    "auth": "http://auth:5102/auth",
    "content": "http://content:5103/content",
    "file": "http://file:5104/files",
    "lien": "http://lien:5105/lien"
}

def safe_post(url, payload):
    try:
        r = requests.post(url, json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}



@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze():

    
    if request.method == "OPTIONS":
        resp = jsonify({"status": "ok"})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return resp, 200

    
    raw = request.json or {}

    print("\n===== ORCHESTRATOR : MAIL REÇU =====")
    print(json.dumps(raw, indent=2, ensure_ascii=False))

    
    parsed = safe_post(PARSER_URL, raw)

    if "analysis_id" not in parsed:
        return jsonify({"error": "Parser n'a pas renvoyé analysis_id"}), 500

    analysis_id = parsed["analysis_id"]
    email_data = parsed["parsed_data"]["email_data"]

    
    results = {}

    enriched_email_data = {
        **email_data,
        "urls": raw.get("urls", []),
        "attachments": raw.get("attachments", [])
    }

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                safe_post,
                url,
                {"email_data": enriched_email_data}
            ): name
            for name, url in SERVICES.items()
        }

        for future in as_completed(futures):
            name = futures[future]
            results[name] = future.result()

    lien_results = results["lien"].get("links_analysis", [])

    for link in lien_results:
        url = link.get("url")
        is_suspicious = link.get("is_suspicious", False)
        db.insert_url_if_missing(analysis_id, url)
        db.update_url_suspicion(analysis_id, url, is_suspicious)

    
    scores = []
    explanations = []

   
    auth_exp = results["auth"].get("explanation", "")
    if auth_exp:
        explanations.append(f"AUTH: {auth_exp}")
    scores.append(results["auth"].get("score", 0))

    
    content_exp = results["content"].get("explanation", "")
    if content_exp:
        explanations.append(f"CONTENT: {content_exp}")
    scores.append(results["content"].get("score", 0))

    
    file_exp = results["file"].get("Explanation", "")
    if file_exp:
        explanations.append(f"FILE: {file_exp}")
    scores.append(results["file"].get("moyenne_pourcentage", 0))

    
    lien_exp = results["lien"].get("explanation", "")
    if lien_exp:
        explanations.append(f"LIEN: {lien_exp}")
    scores.append(results["lien"].get("score", 0))

    score_cyber = round(sum(scores) / len(scores), 2)
    explanation_cyber = " | ".join(filter(None, explanations))

    
    final = {
        "email_data": enriched_email_data,
        "auth": results["auth"],
        "content": results["content"],
        "lien": results["lien"],
        "file": results["file"],
        "explanation_cyber": explanation_cyber,
        "score_cyber": score_cyber,
        "analysis_id": analysis_id,
        "analyzed_at": datetime.utcnow().isoformat()
    }

    
    with open(STORAGE_DIR / f"analysis_{analysis_id}.json", "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    
    db.update_cyber_results(analysis_id, explanation_cyber, score_cyber)
    db.update_status(analysis_id, "processing")

    return jsonify(final)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5106)
