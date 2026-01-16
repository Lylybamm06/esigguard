def apply_rules(email):
    score = 0
    reasons = []

    if "urgent" in email.subject.lower():
        score += 25
        reasons.append("Objet contenant un mot d’urgence")

    if len(email.links) >= 3:
        score += 15
        reasons.append("Nombre élevé de liens")

    if email.has_attachments:
        score += 10
        reasons.append("Présence de pièce jointe")

    return score, reasons
