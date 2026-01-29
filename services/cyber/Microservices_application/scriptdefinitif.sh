#!/bin/bash

################################################################################
# ESIG'GUARD - SCRIPT DE DÉPLOIEMENT COMPLET
# Système de détection de phishing par analyse d'emails
# Ce script installe et configure TOUT automatiquement
################################################################################

set -e  # Arrêter en cas d'erreur

echo ""
echo "=============================================================================="
echo "🛡️  ESIG'GUARD - DÉPLOIEMENT AUTOMATIQUE"
echo "=============================================================================="
echo ""

# Vérifier que le script est exécuté depuis le bon dossier
if [ ! -f "docker-compose.yml" ] || [ ! -d "database" ]; then
    echo -e "${RED}❌ ERREUR : Ce script doit être exécuté depuis le dossier ~/essai${NC}"
    echo "Commande correcte : cd ~/essai && ./deploy_esigguard.sh"
    exit 1
fi

echo -e "${GREEN}✅ Dossier de travail : $(pwd)${NC}"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
PROJECT_DIR="$(pwd)"  # Utilise le dossier courant
MYSQL_HOST="esigguard-mysql.mysql.database.azure.com"
MYSQL_USER="mysql_admin"
MYSQL_PASSWORD="@Ping632026@"
MYSQL_DATABASE="david"

################################################################################
# ÉTAPE 1 : VÉRIFICATION DES PRÉREQUIS
################################################################################

echo -e "${BLUE}📋 ÉTAPE 1/10 : Vérification des prérequis${NC}"

# Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker non installé. Installation...${NC}"
    sudo apt update
    sudo apt install -y docker.io docker-compose
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✅ Docker installé${NC}"
else
    echo -e "${GREEN}✅ Docker déjà installé${NC}"
fi

# MySQL client
if ! command -v mysql &> /dev/null; then
    echo -e "${YELLOW}⚠️  MySQL client non installé. Installation...${NC}"
    sudo apt install -y mysql-client
    echo -e "${GREEN}✅ MySQL client installé${NC}"
else
    echo -e "${GREEN}✅ MySQL client déjà installé${NC}"
fi

# jq (optionnel mais utile)
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq non installé. Installation...${NC}"
    sudo apt install -y jq
    echo -e "${GREEN}✅ jq installé${NC}"
else
    echo -e "${GREEN}✅ jq déjà installé${NC}"
fi

################################################################################
# ÉTAPE 2 : VÉRIFICATION CONNEXION MYSQL AZURE
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 2/10 : Vérification connexion MySQL Azure${NC}"

if mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" &> /dev/null; then
    echo -e "${GREEN}✅ Connexion MySQL Azure réussie${NC}"
else
    echo -e "${RED}❌ ERREUR : Impossible de se connecter à MySQL Azure${NC}"
    echo "Vérifiez :"
    echo "  - Host : $MYSQL_HOST"
    echo "  - User : $MYSQL_USER"
    echo "  - Firewall Azure configuré (IP autorisée)"
    exit 1
fi

################################################################################
# ÉTAPE 3 : CONFIGURATION BASE DE DONNÉES
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 3/10 : Configuration base de données${NC}"

# Vérifier si la base existe
DB_EXISTS=$(mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SHOW DATABASES LIKE '$MYSQL_DATABASE';" | grep -c "$MYSQL_DATABASE" || true)

if [ "$DB_EXISTS" -eq "0" ]; then
    echo -e "${YELLOW}⚠️  Base de données inexistante. Création...${NC}"
    mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "CREATE DATABASE $MYSQL_DATABASE;"
    echo -e "${GREEN}✅ Base de données créée${NC}"
else
    echo -e "${GREEN}✅ Base de données existe déjà${NC}"
fi

# Vérifier si upload_date a une valeur par défaut
echo -e "${YELLOW}🔧 Configuration de la colonne upload_date...${NC}"
mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" << 'EOF'
ALTER TABLE analyses MODIFY COLUMN upload_date DATETIME DEFAULT CURRENT_TIMESTAMP;
EOF
echo -e "${GREEN}✅ Colonne upload_date configurée${NC}"

################################################################################
# ÉTAPE 4 : CRÉATION STRUCTURE PROJET
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 4/10 : Création structure projet${NC}"

cd "$PROJECT_DIR"

# Créer dossiers manquants
mkdir -p test_emails
mkdir -p results

# Corriger permissions si nécessaire
if [ ! -w results ]; then
    echo -e "${YELLOW}🔧 Correction permissions results...${NC}"
    sudo chown -R $USER:$USER results 2>/dev/null || true
fi

chmod 755 results 2>/dev/null || sudo chmod 755 results

echo -e "${GREEN}✅ Structure projet créée${NC}"

################################################################################
# ÉTAPE 5 : VÉRIFICATION EMAIL DE TEST
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 5/10 : Vérification email de test${NC}"

if [ ! -f "test_emails/test_email.eml" ]; then
    echo -e "${RED}❌ ERREUR : Fichier test_emails/test_email.eml introuvable !${NC}"
    echo "Veuillez placer votre fichier email dans : $(pwd)/test_emails/test_email.eml"
    exit 1
fi

echo -e "${GREEN}✅ Email de test trouvé : test_emails/test_email.eml${NC}"

################################################################################
# ÉTAPE 6 : VÉRIFICATION FICHIER .env
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 6/10 : Vérification fichier .env${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Fichier .env manquant !${NC}"
    echo "Créez le fichier .env avec vos clés API"
    exit 1
fi

# Vérifier que les variables essentielles existent
source .env

if [ -z "$MYSQL_HOST" ]; then
    echo -e "${RED}❌ MYSQL_HOST manquant dans .env${NC}"
    exit 1
fi

if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" == "votre_cle_groq" ]; then
    echo -e "${YELLOW}⚠️  GROQ_API_KEY non configurée (fonctionnement en mode dégradé)${NC}"
fi

echo -e "${GREEN}✅ Fichier .env configuré${NC}"

################################################################################
# ÉTAPE 7 : NETTOYAGE DOCKER
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 7/10 : Nettoyage Docker${NC}"

echo -e "${YELLOW}🧹 Arrêt des conteneurs existants...${NC}"
sudo docker-compose down 2>/dev/null || true

echo -e "${YELLOW}🧹 Suppression des anciennes images...${NC}"
sudo docker system prune -f

echo -e "${GREEN}✅ Nettoyage terminé${NC}"

################################################################################
# ÉTAPE 8 : BUILD DOCKER
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 8/10 : Build des conteneurs Docker${NC}"

echo -e "${YELLOW}🔨 Build en cours (peut prendre 5-10 minutes)...${NC}"
sudo docker-compose build --no-cache

echo -e "${GREEN}✅ Build terminé${NC}"

################################################################################
# ÉTAPE 9 : DÉMARRAGE SERVICES
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 9/10 : Démarrage des services${NC}"

sudo docker-compose up -d

echo -e "${YELLOW}⏳ Attente démarrage des services (30 secondes)...${NC}"
sleep 30

# Vérifier que tous les services sont up
echo -e "${YELLOW}🔍 Vérification des services...${NC}"
sudo docker-compose ps

echo -e "${GREEN}✅ Services démarrés${NC}"

################################################################################
# ÉTAPE 10 : TESTS AUTOMATISÉS
################################################################################

echo ""
echo -e "${BLUE}📋 ÉTAPE 10/10 : Tests automatisés${NC}"

# Nettoyer la base
echo -e "${YELLOW}🧹 Nettoyage base de données...${NC}"
mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" << 'EOF'
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE analyses;
TRUNCATE TABLE attachments;
TRUNCATE TABLE urls;
SET FOREIGN_KEY_CHECKS = 1;
EOF

# Créer analyse
echo -e "${YELLOW}📧 Création analyse...${NC}"
mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" << 'EOF'
INSERT INTO analyses (raw_file_path, upload_date) 
VALUES ('/mnt/emails/test_email.eml', NOW());
EOF

ANALYSIS_ID=$(mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" -se "SELECT id FROM analyses ORDER BY id DESC LIMIT 1;")

echo -e "${GREEN}✅ Analyse créée (ID: $ANALYSIS_ID)${NC}"

# Parser
echo -e "${YELLOW}📝 Parsing email...${NC}"
sleep 5
curl -s -X POST http://localhost:5001/process/$ANALYSIS_ID > /dev/null

# Vérifier parsing
SUBJECT=$(mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -D "$MYSQL_DATABASE" -se "SELECT email_subject FROM analyses WHERE id=$ANALYSIS_ID;")

if [ -z "$SUBJECT" ]; then
    echo -e "${RED}❌ Erreur parsing${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Parsing réussi : $SUBJECT${NC}"

# Orchestration
echo -e "${YELLOW}🎯 Orchestration...${NC}"
sleep 5
ORCHESTRATE_RESULT=$(curl -s -X POST http://localhost:5002/orchestrate/$ANALYSIS_ID)

# Vérifier score
SCORE=$(echo "$ORCHESTRATE_RESULT" | jq -r '.score_cyber')

if [ "$SCORE" == "null" ] || [ -z "$SCORE" ]; then
    echo -e "${RED}❌ Erreur orchestration${NC}"
    echo "$ORCHESTRATE_RESULT" | jq
    exit 1
fi

echo -e "${GREEN}✅ Orchestration réussie${NC}"

# Vérifier fichiers results
if [ -d "results/analysis_$ANALYSIS_ID" ]; then
    FILE_COUNT=$(ls -1 results/analysis_$ANALYSIS_ID/*.json 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ Fichiers results créés : $FILE_COUNT fichiers JSON${NC}"
else
    echo -e "${YELLOW}⚠️  Dossier results non créé${NC}"
fi

################################################################################
# RÉSULTAT FINAL
################################################################################

echo ""
echo "=============================================================================="
echo -e "${GREEN}🎉 DÉPLOIEMENT TERMINÉ AVEC SUCCÈS !${NC}"
echo "=============================================================================="
echo ""
echo -e "${BLUE}📊 RÉSULTAT DE L'ANALYSE${NC}"
echo ""
echo "$ORCHESTRATE_RESULT" | jq '{
  analysis_id,
  score_cyber,
  details: {
    smtp: .details.smtp.score,
    auth: .details.auth.score,
    lien: .details.lien.score,
    file: .details.file.score,
    content: .details.content.score
  }
}'
echo ""
echo -e "${BLUE}📁 Fichiers résultats :${NC} $(pwd)/results/analysis_$ANALYSIS_ID/"
echo ""
echo -e "${BLUE}🔗 Services disponibles :${NC}"
echo "  • Parser       : http://localhost:5001"
echo "  • Orchestrator : http://localhost:5002"
echo "  • Auth         : http://localhost:5003"
echo "  • Lien         : http://localhost:5004"
echo "  • File         : http://localhost:5005"
echo "  • Content      : http://localhost:5006"
echo "  • SMTP         : http://localhost:5007"
echo ""
echo -e "${BLUE}📖 Commandes utiles :${NC}"
echo "  • Voir logs    : sudo docker-compose logs -f [service]"
echo "  • Arrêter tout : sudo docker-compose down"
echo "  • Redémarrer   : sudo docker-compose restart"
echo ""
echo -e "${GREEN}✅ ESIG'Guard est opérationnel !${NC}"
echo "=============================================================================="
echo ""
