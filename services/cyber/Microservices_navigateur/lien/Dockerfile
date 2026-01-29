FROM python:3.11-slim

# Dossier de travail dans le conteneur
WORKDIR /app

# Copier les fichiers nécessaires
COPY lien.py .
COPY parser_utils.py .
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Créer le dossier de stockage (au cas où)
RUN mkdir -p /app/storage/lien

# Exposer le port utilisé par Flask
EXPOSE 5105

# Définir l'application Flask explicitement
ENV FLASK_APP=lien.py
ENV FLASK_ENV=production

# Lancer le microservice
CMD ["python", "lien.py"]
