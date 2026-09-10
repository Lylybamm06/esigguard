"""
Scoring d'un email par un modèle de Machine Learning entraîné localement
(TF-IDF + régression logistique — voir data-ml/ pour l'entraînement et les métriques).

Remplace l'ancien pipeline qui transférait l'email vers une VM Azure dédiée
(services/ssh_transfer.py) pour analyse : cette VM n'existe plus, le scoring
se fait donc directement ici, en local, sans dépendance externe.
"""

from pathlib import Path
from functools import lru_cache

import joblib

MODELS_DIR = Path(__file__).resolve().parent.parent / "ml_models"
VECTORIZER_PATH = MODELS_DIR / "tfidf_vectorizer.joblib"
CLASSIFIER_PATH = MODELS_DIR / "phishing_classifier.joblib"

# Seuils sur le score de risque (0-100 = probabilité de phishing estimée)
THRESHOLD_SUSPICIOUS = 30
THRESHOLD_DANGEROUS = 70

TOP_N_REASONS = 5


@lru_cache(maxsize=1)
def _load_model():
    vectorizer = joblib.load(VECTORIZER_PATH)
    classifier = joblib.load(CLASSIFIER_PATH)
    return vectorizer, classifier


def _risk_level(score: int) -> str:
    if score >= THRESHOLD_DANGEROUS:
        return "dangerous"
    if score >= THRESHOLD_SUSPICIOUS:
        return "suspicious"
    return "safe"


def _top_reasons(vectorizer, classifier, text: str) -> list[str]:
    """
    Explique la prédiction : renvoie les mots du mail qui ont le plus
    contribué au score de risque (poids TF-IDF × coefficient du modèle),
    côté positif (vers "phishing") uniquement.
    """
    vec = vectorizer.transform([text])
    coefs = classifier.coef_[0]

    contributions = {}
    for idx in vec.nonzero()[1]:
        weight = vec[0, idx] * coefs[idx]
        if weight > 0:
            word = vectorizer.get_feature_names_out()[idx]
            contributions[word] = weight

    top_words = sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N_REASONS]

    if not top_words:
        return ["Aucun indicateur textuel fort détecté."]

    return [f"Terme suspect détecté : « {word} »" for word, _ in top_words]


def score_email(subject: str, body: str, links: list[str] | None = None, has_attachments: bool = False) -> dict:
    """
    Calcule un score de risque de phishing (0-100), un niveau de risque,
    et une liste de raisons lisibles, à partir du sujet et du corps d'un email.
    """
    vectorizer, classifier = _load_model()

    text = f"{subject or ''} {body or ''}".strip()
    if not text:
        return {
            "score": 0,
            "risk_level": "safe",
            "reasons": ["Email vide ou illisible."],
        }

    proba_phishing = classifier.predict_proba(vectorizer.transform([text]))[0][1]
    score = int(round(proba_phishing * 100))

    reasons = _top_reasons(vectorizer, classifier, text)

    # Signaux structurels complémentaires (non appris par le modèle texte)
    link_count = len(links or [])
    if link_count >= 5:
        reasons.append(f"{link_count} liens détectés dans le message (volume élevé).")
    if has_attachments:
        reasons.append("Le message contient une ou plusieurs pièces jointes.")

    return {
        "score": score,
        "risk_level": _risk_level(score),
        "reasons": reasons,
    }
