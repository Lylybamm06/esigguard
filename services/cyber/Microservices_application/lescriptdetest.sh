#!/bin/bash

################################################################################
# ESIG'GUARD - SCRIPT DE DÉPLOIEMENT + TRAITEMENT DES ANALYSES
################################################################################

set -e

echo ""
echo "=============================================================================="
echo "🛡  ESIG'GUARD - DÉPLOIEMENT + TRAITEMENT AUTOMATIQUE"
echo "=============================================================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
PROJECT_DIR="$(pwd)"
MYSQL_HOST="esigguard-mysql.mysql.database.azure.com"
MYSQL_USER="mysql_admin"
MYSQL_PASSWORD="@Ping632026@"
MYSQL_DATABASE="esigguard_data"

################################################################################
# ÉTAPE 1 : PRÉREQUIS
################################################################################

echo -e "${BLUE}📋 ÉTAPE 1/10 : Vérification des prérequis${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker non installé. Installation...${NC}"
    sudo apt update
    sudo apt install -y docker.io docker-compose
    sudo usermod -aG docker $USER
else
    echo -e "${GREEN}✅ Docker OK${NC}"
fi

if ! command -v mysql &> /dev/null; then
    echo -e "${YELLOW}⚠ MySQL client non installé. Installation...${NC}"
    sudo apt install -y mysql-client
else
    echo -e "${GREEN}✅ MySQL client OK${NC}"
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠ jq non installé. Installation...${NC}"
    sudo apt install -y jq
else
    echo -e "${GREEN}✅ jq OK${NC}"
fi

################################################################################
# ÉTAPE 2 : CONNEXION MYSQL
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 2/10 : Vérification connexion MySQL Azure${NC}"

if mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" &> /dev/null; then
    echo -e "${GREEN}✅ Connexion MySQL OK${NC}"
else
    echo -e "${RED}❌ Impossible de se connecter à MySQL${NC}"
    exit 1
fi

################################################################################
# ÉTAPE 3 : STRUCTURE PROJET
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 3/10 : Vérification structure projet${NC}"

mkdir -p test_emails
mkdir -p results

chmod 755 results || sudo chmod 755 results

echo -e "${GREEN}✅ Dossiers OK${NC}"

################################################################################
# ÉTAPE 4 : .env
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 4/10 : Vérification fichier .env${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Fichier .env manquant${NC}"
    exit 1
fi

source .env

echo -e "${GREEN}✅ .env OK${NC}"

################################################################################
# ÉTAPE 5 : NETTOYAGE DOCKER
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 5/10 : Nettoyage Docker${NC}"

sudo docker-compose down || true
sudo docker system prune -f

echo -e "${GREEN}✅ Docker nettoyé${NC}"

################################################################################
# ÉTAPE 6 : BUILD DOCKER
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 6/10 : Build des conteneurs${NC}"

sudo docker-compose build --no-cache

echo -e "${GREEN}✅ Build terminé${NC}"

################################################################################
# ÉTAPE 7 : DÉMARRAGE SERVICES
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 7/10 : Démarrage des services${NC}"

sudo docker-compose up -d

echo -e "${YELLOW}⏳ Attente 20 secondes...${NC}"
sleep 20

################################################################################
# ÉTAPE 8 : VÉRIFICATION SERVICES
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 8/10 : Vérification des services${NC}"

sudo docker-compose ps

echo -e "${GREEN}✅ Tous les services sont lancés${NC}"

################################################################################
# ÉTAPE 9 : TRAITEMENT DES ANALYSES
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 9/10 : Recherche des analyses en attente${NC}"

ANALYSES=$(mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" -N -e \
"SELECT id, raw_file_path FROM analyses WHERE status='pending';")

if [ -z "$ANALYSES" ]; then
    echo -e "${YELLOW}⚠ Aucune analyse en attente${NC}"
else
    echo -e "${GREEN}📨 Analyses trouvées :${NC}"
    echo "$ANALYSES"
fi

echo ""
echo -e "${BLUE}📋 ÉTAPE 10/10 : Traitement des analyses${NC}"

while read -r id raw_file_path; do
    if [ -z "$id" ]; then
        continue
    fi

    echo ""
    echo -e "${YELLOW}➡ Traitement analyse ID=$id${NC}"
    echo "   Fichier : $raw_file_path"

    # Appel du parser
    echo -e "${BLUE}📤 Appel du parser...${NC}"
    curl -s -X POST "http://localhost:5001/process/$id"
    echo ""

    echo -e "${YELLOW}⏳ Attente 5 secondes...${NC}"
    sleep 5

    # Appel orchestrateur
    echo -e "${BLUE}📡 Appel de l'orchestrateur...${NC}"
    curl -s -X POST "http://localhost:5002/orchestrate/$id"
    echo ""

done <<< "$ANALYSES"

################################################################################
# FIN
################################################################################

echo ""
echo "=============================================================================="
echo -e "${GREEN}🎉 DÉPLOIEMENT + TRAITEMENT TERMINÉ${NC}"
echo "=============================================================================="
echo ""
