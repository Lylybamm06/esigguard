#!/bin/bash

################################################################################
# ESIG'GUARD - SCRIPT DE DÉPLOIEMENT + TRAITEMENT CONTINU DES ANALYSES
################################################################################

set -e

echo ""
echo "=============================================================================="
echo "🛡  ESIG'GUARD - DÉPLOIEMENT + TRAITEMENT AUTOMATIQUE (MODE CONTINU)"
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
MYSQL_DATABASE="david"

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

chmod 755 results ||  chmod 755 results

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

 docker-compose down || true
 docker system prune -f

echo -e "${GREEN}✅ Docker nettoyé${NC}"

################################################################################
# ÉTAPE 6 : BUILD DOCKER
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 6/10 : Build des conteneurs${NC}"

 docker-compose build --no-cache

echo -e "${GREEN}✅ Build terminé${NC}"

################################################################################
# ÉTAPE 7 : DÉMARRAGE SERVICES
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 7/10 : Démarrage des services${NC}"

 docker-compose up -d

echo -e "${YELLOW}⏳ Attente 20 secondes...${NC}"
sleep 20

################################################################################
# ÉTAPE 8 : VÉRIFICATION SERVICES
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 8/10 : Vérification des services${NC}"

 docker-compose ps

echo -e "${GREEN}✅ Tous les services sont lancés${NC}"

################################################################################
# ÉTAPE 9 & 10 : MODE CONTINU - TRAITEMENT DES ANALYSES
################################################################################

echo ""
echo -e "${BLUE}📋 MODE CONTINU : Surveillance des analyses en attente${NC}"
echo -e "${BLUE}🔄 Le script tourne en boucle infinie. CTRL+C pour arrêter.${NC}"
echo ""

while true; do

    ANALYSES=$(mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" -N -e \
    "SELECT id, raw_file_path FROM analyses WHERE status='pending';")

    if [ -z "$ANALYSES" ]; then
        echo -e "${YELLOW}⏳ Aucune analyse en attente. Nouvelle vérification dans 10 secondes...${NC}"
        sleep 10
        continue
    fi

    echo -e "${GREEN}📨 Nouvelles analyses détectées :${NC}"
    echo "$ANALYSES"

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

    echo -e "${GREEN}✔ Cycle terminé. Nouvelle vérification dans 5 secondes.${NC}"
    sleep 5

done
