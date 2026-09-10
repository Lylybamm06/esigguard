# ESIG'Guard — Modèle de scoring phishing

Modèle de classification texte (phishing vs légitime) utilisé par le backend pour scorer un email (`backend/app/services/ml_scoring.py`). Remplace l'ancien pipeline qui envoyait l'email vers une VM Azure dédiée à l'analyse (service aujourd'hui décommissionné) : le scoring se fait désormais en local, sans dépendance externe.

## Dataset

6 corpus publics combinés (~82 400 emails après nettoyage/déduplication, classes équilibrées ≈ 48% légitime / 52% phishing) :

| Source | Contenu | Emails (après nettoyage) |
|---|---|---|
| CEAS_08 | CEAS 2008 Challenge (spam/légitime) | ~39 000 |
| Enron | Enron-Spam (emails d'entreprise légitimes + spam injecté) | ~30 000 |
| Ling | Ling-Spam (liste de diffusion linguistique + spam) | ~2 900 |
| Nazario | Nazario Phishing Corpus (100% phishing) | ~1 600 |
| Nigerian_Fraud | Corpus arnaques "419" (100% phishing) | ~3 300 |
| SpamAssassin | SpamAssassin public corpus | ~5 800 |

Compilation source : [rokibulroni/Phishing-Email-Dataset](https://github.com/rokibulroni/Phishing-Email-Dataset) sur GitHub — les fichiers ne sont pas committés dans ce repo (trop volumineux, ~150 Mo), voir `download_dataset.py` pour les récupérer.

## Méthode

1. `download_dataset.py` télécharge les 6 CSV sources dans `raw/`.
2. `train_model.py` :
   - nettoie chaque source (labels invalides/manquants supprimés) ;
   - combine sujet + corps en un seul champ texte, déduplique ;
   - vectorise avec TF-IDF (unigrammes + bigrammes, 30 000 features max) ;
   - entraîne une régression logistique (`class_weight="balanced"`) ;
   - exporte le vectorizer et le modèle dans `backend/app/ml_models/`.

Choix TF-IDF + régression logistique plutôt qu'un modèle plus complexe : rapide à entraîner et à exécuter (pas de GPU nécessaire), et surtout **interprétable** — pour chaque email, on peut extraire les mots qui ont le plus contribué au score (voir `_top_reasons` dans `ml_scoring.py`), ce qui permet d'afficher une explication lisible plutôt qu'un score opaque.

## Résultats (jeu de test, 15% des données, non vu à l'entraînement)

- **Accuracy** : 0.99
- **ROC AUC** : 0.999
- Précision/rappel équilibrés entre les deux classes (~0.98-0.99 chacune)

**À prendre avec un recul critique** : ce score très élevé reflète surtout le fait que les corpus phishing/légitime utilisés ont un vocabulaire assez distinct (c'est un résultat connu et reproductible sur ce jeu de données précis, pas une garantie de performance en conditions réelles). Sur un email Gmail extrait via l'extension navigateur (texte plus court, sans les en-têtes complets qu'ont les emails des corpus), la performance réelle est probablement plus proche de 85-90% que de 99% — c'est une limite honnête à garder en tête, et un axe d'amélioration possible (ex: collecter et annoter de vrais exemples Gmail pour affiner le modèle).

## Ré-entraîner le modèle

```bash
cd data-ml
pip install -r requirements.txt
python download_dataset.py
python train_model.py
```

Le modèle est ré-exporté directement dans `backend/app/ml_models/` — redémarrer l'API pour qu'elle charge la nouvelle version.

## Pistes d'amélioration

- Ajouter des features structurelles (nombre de liens, présence d'IP brute dans une URL, domaine expéditeur vs domaine des liens) en complément du texte.
- Collecter un petit jeu d'emails Gmail réels (anonymisés) pour évaluer/affiner le modèle sur des données plus proches de l'usage réel de l'extension.
- Essayer un modèle plus expressif (gradient boosting sur features combinées texte + structure) si le besoin de précision augmente.
