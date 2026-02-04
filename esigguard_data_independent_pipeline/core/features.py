def extract_features(row):
    subject = str(row["email_subject"] or "")
    body = str(row["email_body"] or "")

    spf_fail = int(row["auth_spf"] != "pass")
    dkim_fail = int(row["auth_dkim"] != "pass")
    dmarc_fail = int(row["auth_dmarc"] != "pass")

    auth_fail_count = spf_fail + dkim_fail + dmarc_fail

    has_suspicious_url = int(row.get("is_suspicious") == 1)
    has_dangerous_attachment = int(row.get("is_dangerous") == 1)

    subject_length = len(subject)
    body_length = len(body)

    body_subject_ratio = body_length / (subject_length + 1)
    short_subject = int(subject_length < 15)

    technical_risk_score = (
        2 * auth_fail_count
        + 3 * has_suspicious_url
        + 4 * has_dangerous_attachment
    )

    URGENT_KEYWORDS = [
        "urgent", "immediately", "verify", "suspend",
        "password", "account", "security", "alert"
    ]

    contains_urgent_words = int(
        any(word in body.lower() for word in URGENT_KEYWORDS)
    )

    BRANDS = ["paypal", "microsoft", "google", "amazon", "apple"]

    mentions_brand = int(
        any(brand in body.lower() for brand in BRANDS)
    )

    return {
        "spf_fail": spf_fail,
        "dkim_fail": dkim_fail,
        "dmarc_fail": dmarc_fail,
        "auth_fail_count": auth_fail_count,
        "auth_severely_misconfigured": int(auth_fail_count >= 2),
        "has_suspicious_url": has_suspicious_url,
        "has_dangerous_attachment": has_dangerous_attachment,
        "subject_length": subject_length,
        "body_length": body_length,
        "body_subject_ratio": body_subject_ratio,
        "short_subject": short_subject,
        "technical_risk_score": technical_risk_score,
        "contains_urgent_words": contains_urgent_words,
        "mentions_brand": mentions_brand,
    }
