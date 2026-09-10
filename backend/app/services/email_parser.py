"""
Parsing d'un fichier .eml (RFC 822) : extrait le sujet, l'expéditeur, le corps
texte et les liens, pour les passer au scoring (voir ml_scoring.py).
"""

import re
from email import message_from_file
from email.message import Message

URL_REGEX = re.compile(r"https?://[^\s\"'<>]+")


def _extract_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="ignore")
        # Repli : pas de text/plain trouvé, on prend le html brut
        for part in msg.walk():
            if part.get_content_type() == "text/html" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="ignore")
        return ""

    payload = msg.get_payload(decode=True)
    if payload is None:
        return msg.get_payload() or ""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="ignore")


def _has_attachments(msg: Message) -> bool:
    if not msg.is_multipart():
        return False
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            return True
    return False


def parse_eml_file(path: str) -> dict:
    """Parse un fichier .eml sur disque et renvoie sujet / expéditeur / corps / liens / pièces jointes."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        msg = message_from_file(f)

    body = _extract_body(msg)
    links = sorted(set(URL_REGEX.findall(body)))

    return {
        "subject": msg.get("Subject", "") or "",
        "sender": msg.get("From", "") or "",
        "body": body,
        "links": links,
        "has_attachments": _has_attachments(msg),
    }
