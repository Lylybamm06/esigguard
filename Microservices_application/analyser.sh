#!/bin/bash

# Vérification du paramètre
if [ -z "$1" ]; then
    echo "Usage : ./analyser.sh <fichier.eml>"
    exit 1
fi

EMAIL_FILE="$1"

echo "📧 Analyse du fichier : $EMAIL_FILE"
echo "🚀 Lancement des microservices..."

# Lancer docker compose avec la variable
sudo EMAIL_FILE="$EMAIL_FILE" docker compose up --build
