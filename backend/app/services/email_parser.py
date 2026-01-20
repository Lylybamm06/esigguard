from email import message_from_string
from email.message import Message
from typing import Dict


def parse_email(raw_email: str) -> Dict[str, str]:
    msg: Message = message_from_string(raw_email)
    return {
        "subject": msg.get("Subject", ""),
        "from": msg.get("From", ""),
        "to": msg.get("To", ""),
        "date": msg.get("Date", ""),
        "body": _get_body(msg),
    }


def _get_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
        return ""
    return msg.get_payload(decode=True).decode(errors="ignore")