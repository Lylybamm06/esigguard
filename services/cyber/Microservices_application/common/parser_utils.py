import os
import email
import mysql.connector
from email import policy
from azure.storage.blob import BlobServiceClient


# ---------------------------------------------------------
# Connexion MySQL Azure
# ---------------------------------------------------------

def fetch_raw_file_path(analysis_id):
    """
    Récupère le chemin du fichier .eml dans la table 'analyses'
    depuis la base MySQL Azure.
    """
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=3306
    )

    cursor = conn.cursor()
    cursor.execute("SELECT raw_file_path FROM analyses WHERE id = %s", (analysis_id,))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        raise ValueError(f"Aucun fichier trouvé pour analysis_id={analysis_id}")

    return row[0]


# ---------------------------------------------------------
# Téléchargement depuis Azure Blob Storage
# ---------------------------------------------------------

def download_eml_from_blob(blob_path):
    """
    Télécharge un fichier .eml depuis Azure Blob Storage
    et le sauvegarde localement dans /tmp/email.eml.
    """
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container = os.getenv("AZURE_STORAGE_CONTAINER")

    if not connection_string or not container:
        raise EnvironmentError("Variables Azure manquantes : AZURE_STORAGE_CONNECTION_STRING ou AZURE_STORAGE_CONTAINER")

    blob_service = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service.get_blob_client(container=container, blob=blob_path)

    local_path = "/tmp/email.eml"

    with open(local_path, "wb") as f:
        f.write(blob_client.download_blob().readall())

    return local_path


# ---------------------------------------------------------
# Parsing local du fichier .eml
# ---------------------------------------------------------

def parse_local_email(path):
    """
    Parse un fichier .eml local et retourne un dictionnaire
    contenant les champs utiles pour les microservices.
    """
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    parsed = {
        "email_id": os.getenv("ANALYSIS_ID"),
        "subject": msg.get("Subject"),
        "from": msg.get("From"),
        "to": msg.get("To"),
        "date": msg.get("Date"),
        "headers": dict(msg.items()),
        "content": "",
        "attachments": [],
        "routing": {
            "received": msg.get_all("Received", [])
        }
    }

    # Extraction du contenu texte + pièces jointes
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()

            if content_type == "text/plain":
                parsed["content"] += part.get_payload(decode=True).decode(errors="ignore")

            elif part.get_filename():
                parsed["attachments"].append({
                    "filename": part.get_filename(),
                    "content_type": content_type,
                    "size": len(part.get_payload(decode=True))
                })
    else:
        parsed["content"] = msg.get_payload(decode=True).decode(errors="ignore")

    return parsed


# ---------------------------------------------------------
# Fonction principale utilisée par tous les microservices
# ---------------------------------------------------------

def load_email_from_analysis_id():
    """
    Fonction centrale :
    - récupère le chemin du .eml dans MySQL
    - télécharge le fichier depuis Azure Blob Storage
    - parse le fichier
    - retourne un dictionnaire prêt pour analyse
    """
    analysis_id = os.getenv("ANALYSIS_ID")
    if not analysis_id:
        raise EnvironmentError("ANALYSIS_ID manquant dans les variables d'environnement")

    # 1. Récupération du chemin dans MySQL
    blob_path = fetch_raw_file_path(analysis_id)

    # 2. Téléchargement depuis Azure
    local_path = download_eml_from_blob(blob_path)

    # 3. Parsing
    return parse_local_email(local_path)
