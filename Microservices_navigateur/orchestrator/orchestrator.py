from flask import Flask, request, jsonify
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import mysql.connector
import os

app = Flask(__name__)

# ============================================================
# 🔵 CLIENT MYSQL
# ============================================================

class DB:
    def __init__(self):
        self.host = os.getenv("MYSQL_HOST", "esigguard-mysql.mysql.database.azure.com")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self.database = os.getenv("MYSQL_DATABASE", "esigguard_data")
        self.user = os.getenv("MYSQL_USER", "mysql_admin")
        self.password = os.getenv("MYSQL_PASSWORD", "@Ping632026@")

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


db = DB()

# ============================================================
# 🔵 CONFIG ORCHESTRATOR
# ============================================================

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

# ============================================================
# 🔵 ROUTE PRINCIPALE
# ============================================================

@app.post("/analyze")
def analyze():
    raw = request.json or {}

    print("\n===== ORCHESTRATOR : MAIL REÇU =====")
    print(json.dumps(raw, indent=2, ensure_ascii=False))

    # 1) PARSER
    parsed = safe_post(PARSER_URL, raw)

    if "analysis_id" not in parsed:
        return jsonify({"error": "Parser n'a pas renvoyé analysis_id"}), 500

    # ⚠️ ID venant du parser = ID MySQL
    analysis_id = parsed["analysis_id"]
    email_data = parsed["parsed_data"]["email_data"]

    # 2) APPELS MICROSERVICES
    results = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                safe_post,
                url,
                {
                    "email_data": {
                        **email_data,
                        "urls": raw.get("urls", [])
                    },
                    "attachments": raw.get("attachments", [])
                }
            ): name
            for name, url in SERVICES.items()
        }

        for future in as_completed(futures):
            name = futures[future]
            results[name] = future.result()

    # ============================================================
    # 🔵 3) SCORE CYBER + EXPLANATION CYBER UNIQUE
    # ============================================================

    scores = []
    explanations = []

    # AUTH
    auth_exp = results["auth"].get("auth_result", {}).get("explanation", "")
    if auth_exp:
        explanations.append(f"AUTH: {auth_exp}")
    scores.append(results["auth"].get("score", 0))

    # CONTENT
    content_exp = results["content"].get("explanation", "")
    if content_exp:
        explanations.append(f"CONTENT: {content_exp}")
    scores.append(results["content"].get("score", 0))

    # FILE
    file_exp = results["file"].get("Explanation", {}).get("raison", "")
    if file_exp:
        explanations.append(f"FILE: {file_exp}")
    scores.append(results["file"].get("moyenne_pourcentage", 0))

    # LIEN
    lien_exp = results["lien"].get("explanation", "")
    if lien_exp:
        explanations.append(f"LIEN: {lien_exp}")
    scores.append(results["lien"].get("score", 0))

    # SCORE FINAL
    score_cyber = round(sum(scores) / len(scores), 2)

    # EXPLANATION CYBER UNIQUE
    explanation_cyber = " | ".join(explanations)

    print("SCORE CYBER =", score_cyber)
    print("EXPLANATION CYBER =", explanation_cyber)

    # ============================================================
    # 🔵 4) STOCKAGE STRUCTURÉ
    # ============================================================

    final = {
        "analysis_id": analysis_id,
        "email_data": email_data,

        "Auth": results["auth"],
        "Content": results["content"],
        "File": results["file"],
        "Lien": results["lien"],

        "score_cyber": score_cyber,
        "explanation_cyber": explanation_cyber,
        "analyzed_at": datetime.utcnow().isoformat()
    }

    with open(STORAGE_DIR / f"analysis_{analysis_id}.json", "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    # 🔥 Mise à jour MySQL
    db.update_cyber_results(analysis_id, explanation_cyber, score_cyber)
    db.update_status(analysis_id, "processing")

    return jsonify(final)

# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5106)
