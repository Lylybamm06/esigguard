import joblib
import numpy as np

MODEL_PATH = "ML/phishing_regression_model.pkl"
model = joblib.load(MODEL_PATH)

def predict_phishing_score_regression(features):
    X = np.array([[
        features["spf_fail"],
        features["dkim_fail"],
        features["dmarc_fail"],
        features["has_suspicious_url"],
        features["has_dangerous_attachment"],
        features["subject_length"],
        features["body_length"],
    ]])

    score = model.predict(X)[0]

    # Safety clamp
    score = max(0, min(100, score))
    return round(float(score), 2)

