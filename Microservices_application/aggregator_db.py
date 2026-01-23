import os
import time
import mysql.connector
from groq import Groq

client = None
try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except: pass

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'), database=os.getenv('DB_NAME')
    )

def aggregate():
    print("Agrégateur démarré.")
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # On attend que Cyber ET Data aient fini
            query = "SELECT * FROM analyses WHERE score_cyber IS NOT NULL AND score_data IS NOT NULL AND final_score IS NULL"
            cursor.execute(query)
            jobs = cursor.fetchall()
            
            for job in jobs:
                s_cyber = job['score_cyber']
                s_data = job['score_data']
                final = int((s_cyber * 0.6) + (s_data * 0.4))
                
                risk = "HIGH" if final > 75 else ("MEDIUM" if final > 40 else "LOW")
                verdict = "DANGER" if final > 75 else ("SUSPECT" if final > 40 else "SÛR")
                
                expl = "Analyse terminée."
                if client:
                    try:
                        resp = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": f"Résume le risque. Score: {final}/100. Pays: {job['sender_country']}."}]
                        )
                        expl = resp.choices[0].message.content
                    except: pass
                
                cursor.execute("UPDATE analyses SET final_score=%s, final_verdict=%s, risk_level=%s, human_explanation=%s, status='done' WHERE id=%s", 
                               (final, verdict, risk, expl, job['id']))
                conn.commit()
                print(f"Verdict rendu Job {job['id']}: {final}")

            conn.close()
            time.sleep(2)
        except Exception as e:
            print(f"Erreur: {e}")
            time.sleep(5)

if __name__ == "__main__":
    time.sleep(10)
    aggregate()