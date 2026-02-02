FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers nécessaires
COPY auth.py .
COPY requirements.txt .
COPY parser_utils.py .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port
EXPOSE 5102

# Lancer l'application
CMD ["python", "auth.py"]
