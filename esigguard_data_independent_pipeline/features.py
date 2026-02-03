def extract_features(row):
    return {
        "spf_fail": int(row["auth_spf"] != "pass"),
        "dkim_fail": int(row["auth_dkim"] != "pass"),
        "dmarc_fail": int(row["auth_dmarc"] != "pass"),
        "has_suspicious_url": int(row.get("is_suspicious") == 1),
        "has_dangerous_attachment": int(row.get("is_dangerous") == 1),
        "subject_length": len(str(row["email_subject"])),
        "body_length": len(str(row["email_body"]))
    }
