import time
import os
import logging
import mysql.connector
from groq import Groq
from dotenv import load_dotenv

# --- 1. CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# CONFIG BDD
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'esigguard-mysql.mysql.database.azure.com'),
    'user': os.getenv('MYSQL_USER', 'mysql_admin'),
    'password': os.getenv('MYSQL_PASSWORD', '@Ping632026@'),
    'database': os.getenv('MYSQL_NAME', 'esigguard_data'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'autocommit': True
}

# CONFIG IA
client = None
try:
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    logger.info("IA Groq connectée (Mode Arbitre).")
except Exception as e:
    logger.error(f"s d'IA: {e}")

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# =========================================================
# LE CERVEAU (IA Arbitre)
# =========================================================

def ask_ai_arbitration(math_score, task):
    """
    Fonction qui demande à l'IA de valider ou corriger le score.
    """
    if not client: 
        return math_score, "SUSPECT", "IA indisponible, score basé sur les règles."

    # Prompt qui force l'IA à prendre une décision binaire sur le score
    prompt = f"""
    Agis comme un expert Cyber. J'ai un doute sur ce mail.
    Mon algorithme mathématique lui donne un score de : {math_score}/100.
    
    DETAILS DU MAIL :
    - Sujet : "{task.get('email_subject')}"
    - Expéditeur : "{task.get('email_sender')}"
    - Contenu (extrait) : "{task.get('email_body', '')[:500]}..."
    - Analyse technique (Data) : {task.get('explanation_data', 'Non disponible')}

    TA MISSION :
    1. Analyse le contenu. Est-ce du Phishing, une Arnaque, ou un Virus ?
    2. Si C'EST DANGEREUX mais que mon score est bas (<80), TU DOIS LE CORRIGER (mets 90 ou 95).
    3. Si c'est légitime, garde mon score bas.
    
    REPONDS UNIQUEMENT SOUS CE FORMAT EXACT :
    SCORE_FINAL: [Ton score corrigé]
    VERDICT: [SÛR / SUSPECT / DANGER]
    EXPLICATION: [Ton explication en 2 phrases simples pour un humain]
    """

    try:
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", # Modèle rapide
            temperature=0.1
        )
        response = chat.choices[0].message.content

        # Valeurs par défaut
        f_score = math_score
        verdict = "SUSPECT"
        expl = "Analyse terminée."

        # Parsing robuste
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith("SCORE_FINAL:"):
                try: 
                    txt = line.replace("SCORE_FINAL:", "").replace("/100", "").strip()
                    f_score = int(txt)
                except: pass
            elif line.startswith("VERDICT:"):
                verdict = line.replace("VERDICT:", "").strip()
            elif line.startswith("EXPLICATION:"):
                expl = line.replace("EXPLICATION:", "").strip()
        
        return f_score, verdict, expl

    except Exception as e:
        logger.error(f"Erreur IA: {e}")
        return math_score, "SUSPECT", "Erreur lors de l'analyse IA."


# =========================================================
# BOUCLE PRINCIPALE (WORKER)
# =========================================================

def run_worker():
    logger.info("AGGREGATOR (Worker Mode) : En attente du service Data...")
    
    while True:
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            
            # --- LA REQUÊTE QUI ATTEND ---
            # On ne prend QUE les lignes où 'score_data' est REMPLI (IS NOT NULL)
            # Tant que le service Data n'a pas écrit, cette requête renvoie vide.
            query = """
                SELECT * FROM analyses 
                WHERE status='processing' 
                AND score_data IS NOT NULL 
		AND score_cyber IS NOT NULL
                AND final_score IS NULL
            """
            cursor.execute(query)
            tasks = cursor.fetchall()

            if not tasks:
                # Si pas de tâches prêtes (ou si Data n'a pas fini), on attend
                time.sleep(1.5)
                continue

            for task in tasks:
                logger.info(f"Traitement ID {task['id']} (Data reçue : {task['score_data']})")

                # 1. Récupération des scores (On est sûr que Data est là)
                s_cyber = task.get('score_cyber') or 0
                s_data = task['score_data'] # Pas de 'or 0' car on sait qu'il est là
                
                # 2. Moyenne Mathématique de base
                math_score = int((s_cyber + s_data) / 2)
                
                # Sécurité : Si l'un des services a détecté une menace forte, on monte le score
                if s_cyber > 70 or s_data > 70:
                    math_score = max(s_cyber, s_data)

                # 3. Arbitrage IA (Le Patron)
                final_score, final_verdict, explanation = ask_ai_arbitration(math_score, task)

                # 4. ÉCRITURE FINALE
                cursor.execute("""
                    UPDATE analyses 
                    SET final_score=%s, final_verdict=%s, human_explanation=%s, status='done'
                    WHERE id=%s
                """, (final_score, final_verdict, explanation, task['id']))
                
                conn.commit()
                logger.info(f"ID {task['id']} CLOS -> Score Final: {final_score} ({final_verdict})")

            cursor.close()

        except Exception as e:
            logger.error(f"Erreur BDD/Boucle: {e}")
            time.sleep(5) 
        finally:
            if conn and conn.is_connected(): conn.close()
        
        time.sleep(1)

if __name__ == "__main__":
    run_worker()
