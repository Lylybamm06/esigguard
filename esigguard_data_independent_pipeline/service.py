import time
import pandas as pd
from db import fetch_dataframe, execute_update
from scoring import compute_score
from config import POLL_INTERVAL

QUERY = """
SELECT
    a.id AS analysis_id,
    a.email_subject,
    a.email_body,
    a.display_name,
    a.email_sender,
    a.auth_spf,
    a.auth_dkim,
    MAX(u.is_suspicious) AS is_suspicious,
    MAX(att.is_dangerous) AS is_dangerous
FROM analyses a
LEFT JOIN urls u ON a.id = u.analysis_id
LEFT JOIN attachments att ON a.id = att.analysis_id
WHERE a.status = 'processing'
  AND a.score_data IS NULL
GROUP BY
    a.id,
    a.email_subject,
    a.email_body,
    a.display_name,
    a.email_sender,
    a.auth_spf,
    a.auth_dkim;
"""

def run_once():
    df = fetch_dataframe(QUERY)

    if df.empty:
        print("[DATA] No emails to process.")
        return

    # Ensure analysis_id is valid
    df["analysis_id"] = pd.to_numeric(df["analysis_id"], errors="coerce")
    df = df.dropna(subset=["analysis_id"])
    df["analysis_id"] = df["analysis_id"].astype(int)

    if df.empty:
        print("[DATA] No emails to process after cleaning.")
        return

    processed = 0

    for _, row in df.iterrows():
        score, explanation = compute_score(row)

        execute_update(
            """
            UPDATE analyses
            SET
                score_data = %s,
                explanation_data = %s
            WHERE id = %s
            """,
            (score, explanation, row["analysis_id"])
        )

        processed += 1

    print(f"[DATA] Processed {processed} email(s).")

def run_forever():
    print("[DATA] Scoring service started.")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[DATA][ERROR] {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_forever()
