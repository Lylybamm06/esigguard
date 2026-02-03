import re

URGENCY_REGEX = r"\b(urg|immediat|asap|now|limit|final|last)\w*\b"
ACTION_REGEX = r"\b(click|pay|confirm|verify|update|login|access)\w*\b"
EMOTION_REGEX = r"\b(alert|warn|risk|issue|problem|fail|block)\w*\b"

def count_regex(text, pattern):
    return len(re.findall(pattern, text))

def sender_mismatch(display_name, sender):
    if not display_name or not sender:
        return 0
    return int(display_name.lower() not in sender.lower())

def compute_score(row):
    subject = str(row.get("email_subject") or "")
    body = str(row.get("email_body") or "")
    text = f"{subject} {body}".lower()

    nb_words = max(1, len(text.split()))

    urg = count_regex(text, URGENCY_REGEX) / nb_words
    act = count_regex(text, ACTION_REGEX) / nb_words
    emo = count_regex(text, EMOTION_REGEX) / nb_words

    explanations = []

    # ───────── AXIS 1: LANGUAGE PRESSURE ─────────
    language_pressure = 0
    if urg > 0.015:
        language_pressure += 1
    if act > 0.015:
        language_pressure += 1
    if emo > 0.015:
        language_pressure += 1

    # ───────── AXIS 2: MESSAGE CONSISTENCY ─────────
    consistency_risk = 0
    if len(body) < 90 and act > 0:
        consistency_risk += 1
    if len(subject) < 10 and len(body) > 120:
        consistency_risk += 1

    # ───────── AXIS 3: SENDER CREDIBILITY ─────────
    sender_risk = 0
    if sender_mismatch(row.get("display_name"), row.get("email_sender")):
        sender = (row.get("email_sender") or "").lower()
        if any(x in sender for x in ["gmail", "yahoo", "outlook", "hotmail"]):
            sender_risk = 2
        else:
            sender_risk = 1

    # ───────── AXIS 4: CONTEXTUAL RISK (IMPLICIT) ─────────
    context_risk = 0
    if row.get("is_dangerous") == 1:
        context_risk += 2
    if row.get("is_suspicious") == 1:
        context_risk += 1

    # ───────── GLOBAL RISK COMBINATION ─────────
    raw_risk = (
        language_pressure * 1.2
        + consistency_risk * 1.0
        + sender_risk * 1.5
        + context_risk * 0.8
    )

    # Non-linear scaling (important for realism)
    score = int(min(40, round(raw_risk ** 1.3 * 6)))

    # ───────── EXPLANATION GENERATION (NON-GENERIC) ─────────
    if score < 10:
        explanations.append(
            "The message shows limited behavioral or linguistic signs commonly associated with phishing attempts"
        )
    elif score < 20:
        explanations.append(
            "Some elements of the message may raise mild concerns regarding intent and sender credibility"
        )
    elif score < 30:
        explanations.append(
            "Multiple aspects of the message suggest a potentially manipulative or misleading intent"
        )
    else:
        explanations.append(
            "The message presents several converging indicators consistent with high-risk phishing scenarios"
        )

    if sender_risk > 0:
        explanations.append(
            "The perceived sender identity does not fully align with the email address used"
        )

    if language_pressure >= 2:
        explanations.append(
            "The wording relies on urgency or action-driven language that may influence user behavior"
        )

    if context_risk > 0:
        explanations.append(
            "Additional contextual elements increase the overall plausibility of a malicious scenario"
        )

    return score, "; ".join(explanations)
