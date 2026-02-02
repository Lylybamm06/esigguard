FROM python:3.11-slim

# Copier les fichiers nécessaires
COPY file.py .
COPY requirements.txt .
COPY parser_utils.py .


# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port
EXPOSE 5104
ENV FLASK_APP=file.py 
ENV FLASK_ENV=production
# Lancer l'application
CMD ["python", "file.py"]



