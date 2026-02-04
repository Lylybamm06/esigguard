def make_decision(score):
    if score >= 0.7:
        return "PHISHING"
    elif score >= 0.4:
        return "SUSPICIOUS"
    else:
        return "LEGIT"

