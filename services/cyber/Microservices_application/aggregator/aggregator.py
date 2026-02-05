import time
import os
import logging
import threading
import mysql.connector
from flask import Flask, jsonify
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# API POUR L'EXTENSION (Port 5306)
app = Flask(__name__)
CORS(app)

# CONFIG BDD
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'esigguard-mysql.mysql.database.azure.com'),
    'user': os.getenv('MYSQL_USER', 'mysql_admin'),
    'password': os.getenv('MYSQL_PASSWORD', '@Ping632026@'),
    'database': os.getenv('MYSQL_NAME', 'esigguard_data'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'autocommit': True
}

# IA
client = None
try:
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
except: pass

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# =========================================================
# PARTIE 1 : REPONDRE A L'EXTENSION (GET)
# =========================================================
@app.route('/result/<task_id>', methods=['GET'])
def get_result(task_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT status, final_score, final_verdict, human_explanation FROM analyses WHERE id = %s"
        cursor.execute(query, (task_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return jsonify(result)
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# PARTIE 2 : WORKER (CALCUL)
# =========================================================
def ask_ai_arbitration(math_score, task):
    if not client: return math_score, "SUSPECT", "IA indisponible."
    
    # --- SECURITE ANTI-CRASH (Fix Erreur 400) ---
    # On s'assure que rien n'est None avant d'envoyer à Groq
    subj = str(task.get('email_subject') or "Sans objet")
    sender = str(task.get('email_sender') or "Inconnu")
    # On coupe le body s'il est trop long pour éviter les erreurs de token
    body = str(task.get('email_body') or "Contenu vide")[:800]
    data_res = str(task.get('explanation_data') or "RAS")

    prompt = f"""
    Analyse ce mail. Score technique: {math_score}/100.
    Sujet: {subj}
    Expéditeur: {sender}
    Contenu: {body}
    Data: {data_res}
    
    Si Arnaque/Phishing évident et score < 80, CORRIGE (mets 95).
    Sinon garde le score.
    
    FORMAT:
    SCORE_FINAL: [Nombre]
    VERDICT: [SÛR/SUSPECT/DANGER]
    EXPLICATION: [Texte court]
    """
    try:
        # Utilisation d'un modèle fiable
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-4-scout-17b-16e-instruct",
            temperature=0.1
        ).choices[0].message.content
        
        f_score, verdict, expl = math_score, "SUSPECT", "Analyse faite."
        for line in resp.split('\n'):
            line = line.strip()
            if "SCORE_FINAL:" in line: 
                try: f_score = int(line.split(':')[1].replace('/100','').strip())
                except: pass
            if "VERDICT:" in line: verdict = line.split(':')[1].strip()
            if "EXPLICATION:" in line: expl = line.split(':')[1].strip()
        return f_score, verdict, expl
    except Exception as e:
        logger.error(f"Erreur Groq (Ignorée): {e}")
        # En cas de pépin IA, on renvoie le score mathématique au lieu de planter
        return math_score, "SUSPECT", "IA momentanément indisponible."

def run_worker_loop():
    logger.info("🔧 Worker STRICT actif (Attente Data + Cyber)...")
    while True:
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            
            # TU AS DEMANDÉ : STRICTEMENT CYBER ET DATA PRÉSENTS
            query = """
                SELECT * FROM analyses 
                WHERE status='processing' 
                AND score_data IS NOT NULL 
                AND score_cyber IS NOT NULL 
                AND final_score IS NULL
            """
            cursor.execute(query)
            tasks = cursor.fetchall()

            for task in tasks:
                logger.info(f"Traitement ID {task['id']}...")
                
                s_cyber = task['score_cyber'] # On sait qu'il est là grâce au SQL
                s_data = task['score_data']
                
                math_score = int((s_cyber + s_data) / 2)
                if s_cyber > 75 or s_data > 75: math_score = max(s_cyber, s_data)

                final_score, final_verdict, explanation = ask_ai_arbitration(math_score, task)

                cursor.execute("""
                    UPDATE analyses 
                    SET final_score=%s, final_verdict=%s, human_explanation=%s, status='done'
                    WHERE id=%s
                """, (final_score, final_verdict, explanation, task['id']))
                conn.commit()
                logger.info(f"--> ID {task['id']} TERMINE : {final_score}")

            conn.close()
        except Exception as e:
            logger.error(f"Erreur Worker: {e}")
        time.sleep(1.5)

if __name__ == "__main__":
    # 1. On lance le worker
    t = threading.Thread(target=run_worker_loop)
    t.daemon = True
    t.start()
    
    # 2. On lance l'API
    logger.info("🚀 AGGREGATOR PRET SUR LE PORT 5306")
    app.run(host='0.0.0.0', port=5306)
