import joblib
import pandas as pd
import os

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "ML",
    "phishing_model.pkl"
)

model = joblib.load(MODEL_PATH)

def predict_phishing_score(features_dict):
    """
    Retourne une probabilité de phishing entre 0 et 1
    """
    df = pd.DataFrame([features_dict])
    proba = model.predict_proba(df)[0][1]
    return float(round(proba, 3))

