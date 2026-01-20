from hashlib import sha256


def compute_email_fingerprint(raw_email: str) -> str:
    return sha256(raw_email.encode("utf-8")).hexdigest()