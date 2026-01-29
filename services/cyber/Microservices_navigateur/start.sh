#!/bin/bash

echo "=== 🚀 LANCEMENT DE L'ARCHITECTURE PHISHING NAVIGATOR ==="

# Vérification docker-compose
if ! command -v docker-compose &> /dev/null
then
    echo "❌ docker-compose n'est pas installé."
    exit 1
fi

echo "🔧 Construction des images..."
docker-compose build

echo ""
echo "▶️ Démarrage des services..."
docker-compose up
