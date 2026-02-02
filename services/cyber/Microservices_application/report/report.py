import json
import os
import mysql.connector

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_to_mysql(analysis_id, data):
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO analysis_results (analysis_id, report_json)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE report_json = VALUES(report_json)
    """, (analysis_id, json.dumps(data)))

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    analysis_id = os.getenv("ANALYSIS_ID")

    report = {
        "analysis_id": analysis_id,
        "files": load_json("/results/file/files.json"),
        "content": load_json("/results/content/content.json"),
        "links": load_json("/results/lien/links.json"),
        "smtp": load_json("/results/smtp/smtp.json")
    }

    os.makedirs("/results", exist_ok=True)
    with open("/results/report.json", "w") as f:
        json.dump(report, f, indent=4)

    save_to_mysql(analysis_id, report)

    print("[REPORT] Rapport global généré.")
