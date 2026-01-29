import time
import os
import logging
import mysql.connector
from groq import Groq

# --- CONFIGURATION LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION BDD ---
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'esigguard-mysql.mysql.database.azure.com'),
    'user': os.getenv('DB_USER', 'mysql_admin'),
    'password': os.getenv('DB_PASSWORD','@Ping632026@'), 
    'database': os.getenv('DB_NAME', 'esigguard_data'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'autocommit': False
}

# --- CONFIGURATION IA (GROQ) ---
GROQ_API_KEY = os.getenv('GROQ_API_KEY','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')
client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("Client Groq initialisé avec succès.")
    except Exception as e:
        logger.error(f"Erreur init Groq: {e}")

def get_db_connection():
    # Retourne une nouvelle connexion MySQL configurée par `DB_CONFIG`.
    # Caller must gérer la fermeture si nécessaire (conn.close()).
    return mysql.connector.connect(**DB_CONFIG)

# --- FONCTION IA ---
def generate_ia_verdict(final_score, cyber_reason, data_reason):
    """
    Utilise Groq pour générer une explication pédagogique et un verdict.
    Retourne un tuple: (verdict_court, explication_longue)
    """
    # 1. Fallback (Si pas de clé API ou erreur)
    if not client:
        return fallback_explanation(final_score, cyber_reason, data_reason)

    try:
        # 2. Le Prompt "Expert Cyber"
        prompt = f"""
        Tu es Esig'Guard, un expert en cybersécurité pédagogique et bienveillant.
        Analyse ce mail :
        - Score de risque global : {final_score}/100 (100 = Danger mortel, 0 = Sûr).
        - Raisons Techniques (Cyber) : {cyber_reason if cyber_reason else "Rien à signaler"}.
        - Raisons Sémantiques (IA Data) : {data_reason if data_reason else "Rien à signaler"}.

        TA MISSION :
        1. Donne un VERDICT COURT en 1 mot (SÛR, SUSPECT, ou DANGER).
        2. Rédige une explication pour l'utilisateur (Max 3 phrases).
           - Explique POURQUOI c'est dangereux en citant les critères critiques détectés ci-dessus.
           - Dis-lui concrètement quoi faire (ex: "Ne cliquez pas", "Supprimez-le").
           - Ton ton doit être rassurant mais ferme. Pas de jargon technique complexe sans explication.
        
        Format de réponse attendu :
        VERDICT: [Le verdict]
        EXPLICATION: [Ton texte]
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192", # Modèle rapide et intelligent
            temperature=0.5,
        )
        
        response = chat_completion.choices[0].message.content
        
        # Parsing basique de la réponse
        verdict = "INCONNU"
        explanation = "Analyse effectuée."
        
        for line in response.split('\n'):
            if line.startswith("VERDICT:"):
                verdict = line.replace("VERDICT:", "").strip()
            elif line.startswith("EXPLICATION:"):
                explanation = line.replace("EXPLICATION:", "").strip()
        
        # Si le parsing échoue, on prend tout le texte
        if verdict == "INCONNU":
            explanation = response
            verdict = "DANGER" if final_score > 70 else "SÛR"

        return verdict, explanation

    except Exception as e:
        logger.error(f"Erreur Groq IA: {e}")
        return fallback_explanation(final_score, cyber_reason, data_reason)

def fallback_explanation(score, c_reason, d_reason):
    """Méthode de secours (si l'IA plante)"""
    if score < 30:
        return "SÛR", "Ce mail semble légitime. Nos analyses ne détectent aucune menace."
    elif score < 70:
        return "SUSPECT", f"Soyez prudent. Éléments suspects détectés : {c_reason}."
    else:
        return "DANGER", "DANGER : Ce mail est une tentative de phishing avérée. Supprimez-le immédiatement."

# --- BOUCLE PRINCIPALE ---
def run_aggregator():
    # Boucle principale qui garde le service à l'écoute.
    # La connexion DB est réutilisée et rétablie automatiquement en cas d'erreur.
    logger.info("AGGREGATOR SERVICE (Mode IA): en attente des tâches...")
    conn = None

    while True:
        try:
            if conn is None or not conn.is_connected():
                conn = get_db_connection()
            
            cursor = conn.cursor(dictionary=True)

            # Requête : On prend ceux qui ont les 2 scores mais pas de verdict final
            query = """
                SELECT * FROM analyses 
                WHERE score_cyber IS NOT NULL 
                AND score_data IS NOT NULL 
                AND final_score IS NULL
            """
            cursor.execute(query)
            tasks = cursor.fetchall()

            for task in tasks:
                analysis_id = task['id']
                logger.info(f"Analyse IA en cours pour ID {analysis_id}...")

                # 1. Calcul du Score Mathématique
                s_cyber = task['score_cyber']
                s_data = task['score_data']
                final_score = int((s_cyber * 0.6) + (s_data * 0.4))

                # 2. Génération du Texte (Appel à Groq)
                verdict_short, human_text = generate_ia_verdict(
                    final_score, 
                    task.get('explanation_cyber'), 
                    task.get('explanation_data')
                )

                # 3. Mise à jour BDD (Sans finished_at comme demandé)
                sql_update = """
                    UPDATE analyses 
                    SET final_score = %s,
                        final_verdict = %s,
                        human_explanation = %s,
                        status = 'done'
                    WHERE id = %s
                """
                cursor.execute(sql_update, (final_score, verdict_short, human_text, analysis_id))
                conn.commit()
                
                logger.info(f"ID {analysis_id} terminé -> Verdict: {verdict_short}")

            cursor.close()
            if not tasks:
                time.sleep(2)

        except mysql.connector.Error as e:
            # Erreurs liées à la DB : fermer la connexion et réessayer après pause
            logger.error(f"Erreur DB: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            time.sleep(5)
        except Exception as e:
            # Erreurs imprévues : journaliser le détail et continuer
            logger.error(f"Erreur générale: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_aggregator()import time
import os
import logging
import mysql.connector
from groq import Groq

# --- CONFIGURATION LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION BDD ---
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'esigguard-mysql.mysql.database.azure.com'),
    'user': os.getenv('DB_USER', 'mysql_admin'),
    'password': os.getenv('DB_PASSWORD','@Ping632026@'), 
    'database': os.getenv('DB_NAME', 'esigguard_data'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'autocommit': False
}

# --- CONFIGURATION IA (GROQ) ---
GROQ_API_KEY = os.getenv('GROQ_API_KEY','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')
client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("Client Groq initialisé avec succès.")
    except Exception as e:
        logger.error(f"Erreur init Groq: {e}")

def get_db_connection():
    # Retourne une nouvelle connexion MySQL configurée par `DB_CONFIG`.
    # Caller must gérer la fermeture si nécessaire (conn.close()).
    return mysql.connector.connect(**DB_CONFIG)

# --- FONCTION IA ---
def generate_ia_verdict(final_score, cyber_reason, data_reason):
    """
    Utilise Groq pour générer une explication pédagogique et un verdict.
    Retourne un tuple: (verdict_court, explication_longue)
    """
    # 1. Fallback (Si pas de clé API ou erreur)
    if not client:
        return fallback_explanation(final_score, cyber_reason, data_reason)

    try:
        # 2. Le Prompt "Expert Cyber"
        prompt = f"""
        Tu es Esig'Guard, un expert en cybersécurité pédagogique et bienveillant.
        Analyse ce mail :
        - Score de risque global : {final_score}/100 (100 = Danger mortel, 0 = Sûr).
        - Raisons Techniques (Cyber) : {cyber_reason if cyber_reason else "Rien à signaler"}.
        - Raisons Sémantiques (IA Data) : {data_reason if data_reason else "Rien à signaler"}.

        TA MISSION :
        1. Donne un VERDICT COURT en 1 mot (SÛR, SUSPECT, ou DANGER).
        2. Rédige une explication pour l'utilisateur (Max 3 phrases).
           - Explique POURQUOI c'est dangereux en citant les critères critiques détectés ci-dessus.
           - Dis-lui concrètement quoi faire (ex: "Ne cliquez pas", "Supprimez-le").
           - Ton ton doit être rassurant mais ferme. Pas de jargon technique complexe sans explication.
        
        Format de réponse attendu :
        VERDICT: [Le verdict]
        EXPLICATION: [Ton texte]
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192", # Modèle rapide et intelligent
            temperature=0.5,
        )
        
        response = chat_completion.choices[0].message.content
        
        # Parsing basique de la réponse
        verdict = "INCONNU"
        explanation = "Analyse effectuée."
        
        for line in response.split('\n'):
            if line.startswith("VERDICT:"):
                verdict = line.replace("VERDICT:", "").strip()
            elif line.startswith("EXPLICATION:"):
                explanation = line.replace("EXPLICATION:", "").strip()
        
        # Si le parsing échoue, on prend tout le texte
        if verdict == "INCONNU":
            explanation = response
            verdict = "DANGER" if final_score > 70 else "SÛR"

        return verdict, explanation

    except Exception as e:
        logger.error(f"Erreur Groq IA: {e}")
        return fallback_explanation(final_score, cyber_reason, data_reason)

def fallback_explanation(score, c_reason, d_reason):
    """Méthode de secours (si l'IA plante)"""
    if score < 30:
        return "SÛR", "Ce mail semble légitime. Nos analyses ne détectent aucune menace."
    elif score < 70:
        return "SUSPECT", f"Soyez prudent. Éléments suspects détectés : {c_reason}."
    else:
        return "DANGER", "DANGER : Ce mail est une tentative de phishing avérée. Supprimez-le immédiatement."

# --- BOUCLE PRINCIPALE ---
def run_aggregator():
    # Boucle principale qui garde le service à l'écoute.
    # La connexion DB est réutilisée et rétablie automatiquement en cas d'erreur.
    logger.info("AGGREGATOR SERVICE (Mode IA): en attente des tâches...")
    conn = None

    while True:
        try:
            if conn is None or not conn.is_connected():
                conn = get_db_connection()
            
            cursor = conn.cursor(dictionary=True)

            # Requête : On prend ceux qui ont les 2 scores mais pas de verdict final
            query = """
                SELECT * FROM analyses 
                WHERE score_cyber IS NOT NULL 
                AND score_data IS NOT NULL 
                AND final_score IS NULL
            """
            cursor.execute(query)
            tasks = cursor.fetchall()

            for task in tasks:
                analysis_id = task['id']
                logger.info(f"Analyse IA en cours pour ID {analysis_id}...")

                # 1. Calcul du Score Mathématique
                s_cyber = task['score_cyber']
                s_data = task['score_data']
                final_score = int((s_cyber * 0.6) + (s_data * 0.4))

                # 2. Génération du Texte (Appel à Groq)
                verdict_short, human_text = generate_ia_verdict(
                    final_score, 
                    task.get('explanation_cyber'), 
                    task.get('explanation_data')
                )

                # 3. Mise à jour BDD (Sans finished_at comme demandé)
                sql_update = """
                    UPDATE analyses 
                    SET final_score = %s,
                        final_verdict = %s,
                        human_explanation = %s,
                        status = 'done'
                    WHERE id = %s
                """
                cursor.execute(sql_update, (final_score, verdict_short, human_text, analysis_id))
                conn.commit()
                
                logger.info(f"ID {analysis_id} terminé -> Verdict: {verdict_short}")

            cursor.close()
            if not tasks:
                time.sleep(2)

        except mysql.connector.Error as e:
            # Erreurs liées à la DB : fermer la connexion et réessayer après pause
            logger.error(f"Erreur DB: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            time.sleep(5)
        except Exception as e:
            # Erreurs imprévues : journaliser le détail et continuer
            logger.error(f"Erreur générale: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_aggregator()
