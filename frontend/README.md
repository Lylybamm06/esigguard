# ESIG'Guard — Dashboard (Frontend)

Dashboard web (React + Vite) pour consulter les analyses d'emails : historique, détail d'une analyse, statistiques de risque, authentification.

## Stack

React 19, React Router, Axios, Vite.

## Structure

```
src/
├── api/            appels HTTP vers le backend (client Axios, services)
├── components/
│   ├── layout/     structure de page (sidebar, topbar, layout)
│   ├── mail/       composants liés à l'analyse d'emails
│   └── ui/         composants génériques (Button, Card, Table, Badge...)
├── pages/          une page par route (Home, Login, Register, Dashboard, Analyze, History, Result)
└── styles/         variables et styles globaux
```

## Lancer en local

```bash
cd frontend
npm install
npm run dev
```

L'application se lance sur `http://localhost:5173` et attend le backend sur `http://127.0.0.1:8000` (voir `src/config.js`).

## Build de production

```bash
npm run build
```
