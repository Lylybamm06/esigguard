def compute_risk(score):
    if score >= 71:
        return "red"
    elif score >= 31:
        return "orange"
    return "green"
