"""
Entraîne le modèle de scoring phishing utilisé par le backend
(backend/app/services/ml_scoring.py).

Pipeline : TF-IDF (unigrammes + bigrammes) -> régression logistique.
Choisi pour rester simple, rapide à entraîner et interprétable (les poids du
modèle permettent d'expliquer une prédiction email par email), suffisant pour
un premier modèle de classification de texte binaire (phishing / légitime).

Prérequis : lancer d'abord `python download_dataset.py` (voir README.md de ce
dossier pour la source et le détail des 6 corpus combinés).

Usage : python train_model.py
Sortie : ../backend/app/ml_models/{tfidf_vectorizer,phishing_classifier}.joblib
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

RAW_DIR = Path(__file__).parent / "raw"
MODELS_DIR = Path(__file__).parent.parent / "backend" / "app" / "ml_models"

SOURCES = ["CEAS_08.csv", "Enron.csv", "Ling.csv", "Nazario.csv", "Nigerian_Fraud.csv", "SpamAssasin.csv"]


def load_and_clean(filename: str) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / filename, engine="python", on_bad_lines="skip")
    df = df[["subject", "body", "label"]].copy()
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    df = df.dropna(subset=["label", "body"])
    df["label"] = df["label"].astype(int)
    df = df[df["label"].isin([0, 1])]
    df["subject"] = df["subject"].fillna("")
    return df


def build_dataset() -> pd.DataFrame:
    frames = [load_and_clean(f) for f in SOURCES]
    combined = pd.concat(frames, ignore_index=True)

    combined["text"] = (combined["subject"] + " " + combined["body"]).str.strip()
    combined = combined[combined["text"].str.len() > 10]
    combined = combined.drop_duplicates(subset=["text"])

    return combined


def main():
    print("Chargement et nettoyage des 6 corpus...")
    df = build_dataset()
    print(f"Dataset final : {len(df)} emails — répartition : {df['label'].value_counts().to_dict()}")

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.15, random_state=42, stratify=df["label"]
    )

    vectorizer = TfidfVectorizer(
        max_features=30000,
        ngram_range=(1, 2),
        min_df=2,
        stop_words="english",
        sublinear_tf=True,
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    clf = LogisticRegression(max_iter=1000, C=1.0, class_weight="balanced")
    clf.fit(X_train_vec, y_train)

    y_pred = clf.predict(X_test_vec)
    y_proba = clf.predict_proba(X_test_vec)[:, 1]

    print("\n=== Rapport de classification (jeu de test, 15%) ===")
    print(classification_report(y_test, y_pred, target_names=["legitime", "phishing"]))
    print("ROC AUC :", round(roc_auc_score(y_test, y_proba), 4))
    print("Matrice de confusion :\n", confusion_matrix(y_test, y_pred))

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, MODELS_DIR / "tfidf_vectorizer.joblib")
    joblib.dump(clf, MODELS_DIR / "phishing_classifier.joblib")
    print(f"\nModèle sauvegardé dans {MODELS_DIR}")


if __name__ == "__main__":
    main()
