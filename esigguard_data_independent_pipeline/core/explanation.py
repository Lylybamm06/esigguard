def build_explanation(features, score_norm):
    """
    Build an analytical, human-readable explanation of the ML score.
    score_norm is a normalized score in [0, 1].
    """

    # 1. Global interpretation
    if score_norm < 0.2:
        risk_level = "low"
        summary = "The ML score indicates a low level of technical risk based on the observed signals."
    elif score_norm < 0.5:
        risk_level = "medium"
        summary = "The ML score indicates a moderate level of technical risk due to a combination of indicators."
    else:
        risk_level = "high"
        summary = "The ML score indicates a high level of technical risk, consistent with phishing-like patterns."

    # 2. Authentication analysis
    auth_fail_count = features.get("auth_fail_count", 0)

    if auth_fail_count == 0:
        auth_analysis = "Email authentication mechanisms (SPF, DKIM, DMARC) are correctly configured."
    elif auth_fail_count == 1:
        auth_analysis = "A single authentication failure was observed, which is relatively common in legitimate automated emails."
    else:
        auth_analysis = "Multiple authentication mechanisms failed, increasing uncertainty about the legitimacy of the sender."

    # 3. Content and behavior analysis
    content_signals = []

    if features.get("has_suspicious_url"):
        content_signals.append("the presence of links that require careful verification")

    if features.get("has_dangerous_attachment"):
        content_signals.append("the presence of potentially dangerous attachments")

    if features.get("contains_urgent_words"):
        content_signals.append("the use of urgency-related language commonly seen in phishing attempts")

    if features.get("mentions_brand"):
        content_signals.append("references to well-known brands, a common social engineering technique")

    if features.get("short_subject"):
        content_signals.append("an unusually short subject line, often associated with low-context messages")

    if content_signals:
        content_analysis = "The email content shows " + ", ".join(content_signals) + "."
    else:
        content_analysis = "No strong behavioral or content-based phishing patterns were detected."

    # 4. Structural analysis
    if features.get("body_subject_ratio", 0) > 20:
        structure_analysis = "The email body is disproportionately long compared to the subject, which may indicate template-based phishing content."
    else:
        structure_analysis = "The structural characteristics of the email are consistent with common legitimate messages."

    # 5. Final explanation object
    explanation = {
        "risk_level": risk_level,
        "ml_score_normalized": round(score_norm, 3),
        "summary": summary,
        "analysis": {
            "authentication": auth_analysis,
            "content": content_analysis,
            "structure": structure_analysis,
        },
        "conclusion": "This score represents a technical risk estimation based on observable email properties and should be interpreted as a complementary signal alongside existing cybersecurity rules.",
    }

    return explanation
