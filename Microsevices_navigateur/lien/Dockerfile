FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers nécessaires
COPY lien.py .
COPY requirements.txt .
COPY parser_utils.py .


# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port
EXPOSE 5002

# Lancer l'application
CMD ["python", "lien.py"]
