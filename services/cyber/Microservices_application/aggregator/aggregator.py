import time
import os
import logging
import mysql.connector
from groq import Groq
from dotenv import load_dotenv

# --- 1. CHARGEMENT ROBUSTE DU .ENV ---
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

# --- CONFIGURATION LOGGING (Format Standard) ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION BDD ---
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'esigguard-mysql.mysql.database.azure.com'),
    'user': os.getenv('DB_USER', 'mysql_admin'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'esigguard_data'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'autocommit': False
}

# --- CONFIGURATION IA ---
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("Client Groq active (Mode Production).")
    except Exception as e:
        logger.error(f"Erreur init Groq: {e}")

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# --- FONCTION SÉCURITÉ (HARD RULES) ---
def calculate_malus(text_cyber, text_data):
    malus = 0
    text_combined = (str(text_cyber) + " " + str(text_data)).lower()
    triggers = {
        'virus': 40, 'malware': 40, '.exe': 30, 'trojan': 40,
        'ransomware': 30, 'blacklist': 25, 'phishing avéré': 20
    }
    for word, points in triggers.items():
        if word in text_combined:
            malus += points
    return min(malus, 50)

# --- FONCTION IA (GÉNÉRATION VERDICT) ---
def generate_ia_verdict(final_score, task_data):
    if not client:
        return fallback_verdict(final_score)

    try:
        # Récupération des données (Gestion des valeurs nulles)
        sender = task_data.get('email_sender') or "Inconnu"
        display = task_data.get('display_name') or "Non spécifié"
        reply_to = task_data.get('reply_to') or "Identique"
        subject = task_data.get('email_subject') or "Sans objet"
        country = task_data.get('sender_country') or "Non localisé"
        
        # Authentification
        spf = task_data.get('auth_spf') or "?"
        dkim = task_data.get('auth_dkim') or "?"

        # Scores et Raisons
        s_cyber = task_data.get('score_cyber', 0)
        s_data = task_data.get('score_data', 0)
        cyber_reason = task_data.get('explanation_cyber') or ""
        data_reason = task_data.get('explanation_data') or ""

        # PROMPT TECHNIQUE
        prompt = f"""
        Agis comme un expert en cybersécurité. Analyse ce mail.
        
        1. IDENTITÉ & AUTHENTIFICATION
        - Expéditeur : {sender}
        - Nom affiché : {display}
        - Reply-To : {reply_to}
        - Pays IP : {country}
        - Auth : SPF={spf}, DKIM={dkim}
        
        2. ANALYSE DU CONTENU
        - Sujet : "{subject}"
        - Analyse Technique (Score: {s_cyber}/100) : {cyber_reason}
        - Analyse Sémantique (Score: {s_data}/100) : {data_reason}
        
        3. RÉSULTAT FINAL
        - Score Global de Risque : {final_score}/100
        
        CONSIGNE :
        Rédige une explication pour l'utilisateur.
        - Si le score est haut, explique pourquoi (ex: "L'adresse de réponse est suspecte").
        - Si c'est un virus, dis-le clairement.
        - Ne sois pas vague. Utilise les données ci-dessus.
        
        FORMAT DE RÉPONSE :
        VERDICT: [SÛR / SUSPECT / DANGER]
        EXPLICATION: [Ton texte clair, direct et pédagogique, minimum 2 phrases]
        """

        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
        response = chat.choices[0].message.content
        
        verdict = "INCONNU"
        explanation = "Analyse terminée."
        
        for line in response.split('\n'):
            if "VERDICT:" in line: verdict = line.replace("VERDICT:", "").strip()
            if "EXPLICATION:" in line: explanation = line.replace("EXPLICATION:", "").strip()
            
        return verdict, explanation

    except Exception as e:
        logger.error(f"Erreur Appel IA: {e}")
        return fallback_verdict(final_score)

def fallback_verdict(score):
    if score > 75: return "DANGER", "Menace critique détectée (Expéditeur ou Contenu)."
    if score > 40: return "SUSPECT", "Soyez vigilant, éléments techniques douteux."
    return "SÛR", "Aucun risque détecté."

# --- BOUCLE PRINCIPALE ---
def run_aggregator():
    logger.info("SERVICE AGGREGATOR V_FINAL: Démarrage...")
    conn = None

    while True:
        try:
            if conn is None or not conn.is_connected():
                conn = get_db_connection()
            
            cursor = conn.cursor(dictionary=True)

            # Sélection des tâches
            query = """
                SELECT * FROM analyses 
                WHERE status = 'processing'
                AND score_cyber IS NOT NULL 
                AND score_data IS NOT NULL 
                AND final_score IS NULL
            """
            cursor.execute(query)
            tasks = cursor.fetchall()

            for task in tasks:
                aid = task['id']
                logger.info(f"Traitement ID {aid} en cours...")

                # 1. Calcul du score final
                s_cyber = task['score_cyber']
                s_data = task['score_data']
                
                base_score = (s_cyber * 0.6) + (s_data * 0.4)
                malus = calculate_malus(task.get('explanation_cyber',''), task.get('explanation_data',''))
                
                final_score = int(min(base_score + malus, 100))
                
                # 2. Appel IA (qui a maintenant accès aux scores s_cyber et s_data via 'task')
                verdict, expl = generate_ia_verdict(final_score, task)

                # 3. Mise à jour BDD
                cursor.execute("""
                    UPDATE analyses 
                    SET final_score = %s, final_verdict = %s, human_explanation = %s, status = 'done'
                    WHERE id = %s
                """, (final_score, verdict, expl, aid))
                
                conn.commit()
                logger.info(f"ID {aid} termine -> Score: {final_score}/100 Verdict: {verdict}")

            cursor.close()
            # Gestion de la pause
            time.sleep(1 if tasks else 2)

        except Exception as e:
            logger.error(f"Exception boucle principale: {e}")
            if conn: 
                try: conn.close()
                except: pass
                conn = None
            time.sleep(5)

if __name__ == "__main__":
    run_aggregator()