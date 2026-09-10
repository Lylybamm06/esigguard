# ESIG'Guard — Extension Gmail

Extension navigateur (Manifest V3) qui s'intègre à Gmail pour déclencher l'analyse anti-phishing d'un email directement depuis la boîte de réception.

## Fonctionnement

- `content.js` s'injecte dans les pages `mail.google.com` et détecte l'email actuellement ouvert.
- `popup.js` / `popup.html` affichent l'interface de l'extension (le popup déclenché par l'icône de la barre d'outils) et communiquent avec l'API backend (`http://127.0.0.1:8000` en développement).
- `manifest.json` déclare les permissions nécessaires (`activeTab`, `tabs`) et les hôtes autorisés (Gmail + API locale).

## Installation en local (mode développeur)

1. Ouvrir `chrome://extensions` dans Chrome.
2. Activer le **Mode développeur** (en haut à droite).
3. Cliquer sur **Charger l'extension non empaquetée**.
4. Sélectionner le dossier `extension/`.
5. L'extension apparaît dans la barre d'outils — le backend (`backend/`) doit être lancé en parallèle sur `http://127.0.0.1:8000` pour que l'analyse fonctionne.
