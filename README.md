# ESIG'Guard

Application de détection de phishing par IA : une extension Gmail et un dashboard web permettent d'analyser un email (expéditeur, contenu, liens, pièces jointes) et d'obtenir un score de risque avec une explication lisible, calculé par un modèle de machine learning entraîné localement.

Projet réalisé initialement dans le cadre du PING (Projet d'Ingénierie) de l'ESIGELEC, repris et développé en solo — extension, backend, frontend et modèle ML.

## Architecture

```
esigguard/
├── extension/    Extension Chrome (Manifest V3) — lit l'email ouvert dans Gmail et demande une analyse
├── backend/      API FastAPI — authentification, upload d'emails, scoring ML, historique, statistiques
├── frontend/     Dashboard React — historique, détail d'une analyse, statistiques de risque
└── data-ml/      Entraînement du modèle de scoring (dataset, script, métriques)
```

**Flux général** : l'extension Gmail (ou l'upload d'un `.eml` depuis le dashboard) envoie le contenu d'un email à l'API ; le backend le score avec un modèle ML entraîné localement (TF-IDF + régression logistique, voir `data-ml/README.md`) et enregistre le résultat (score, verdict, explication) en base SQLite locale, consultable depuis le dashboard.

Ce scoring tournait à l'origine sur une VM Azure séparée (transfert par SSH) ; cette VM n'existant plus, le scoring se fait maintenant directement dans l'API, sans dépendance externe — voir `backend/app/services/ml_scoring.py`.

## Stack technique

- **Extension** : JavaScript (Manifest V3)
- **Backend** : Python, FastAPI, SQLite, scikit-learn (scoring), bcrypt, JWT (auth)
- **Frontend** : React 19, Vite, React Router, Axios
- **ML** : TF-IDF + régression logistique (scikit-learn), entraîné sur ~82 000 emails (6 corpus publics combinés — détails dans `data-ml/README.md`)

## Installation

### Base de données

Rien à installer : l'API utilise SQLite (fichier local `backend/esigguard.db`), créé et initialisé automatiquement au premier démarrage. `backend/schema.sql` documente le schéma à titre indicatif.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate sous Windows
pip install -r requirements.txt
cp .env.example .env       # puis renseigner les vraies valeurs (voir ci-dessous)
uvicorn app.main:app --reload
```

L'API tourne sur `http://127.0.0.1:8000` (documentation interactive sur `/docs`). Le modèle ML pré-entraîné est déjà inclus dans `backend/app/ml_models/` — aucune étape d'entraînement n'est nécessaire pour lancer l'API.

**Variables d'environnement (`backend/.env`)**, voir `backend/.env.example` :
- `JWT_SECRET` — secret de signature des tokens de session (obligatoire, à générer soi-même)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard sur `http://localhost:5173`.

### Extension

Voir `extension/README.md` pour le chargement en mode développeur dans Chrome.

## État actuel

- Authentification, upload d'email, scoring ML, historique et statistiques sont fonctionnels de bout en bout côté API et dashboard.
- Les routes `/api/analyses`, `/api/upload` et `/api/stats` sont protégées par token JWT (obtenu au login) ; `/score` reste ouverte, c'est la route appelée directement par l'extension Chrome.
- L'extension appelle `POST /score` (implémenté, `backend/app/api/score.py`) avec le contenu extrait de Gmail et reçoit un score en direct.

## Sécurité

Aucun identifiant réel n'est présent dans ce repo. Voir `backend/.env.example` pour la liste des variables à renseigner en local.
