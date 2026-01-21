import os
import json
import email
import re
from email import policy
from email.parser import BytesParser
from datetime import datetime

def extract_urls(text):
    if not text:
        return []
    return re.findall(r'https?://[^\s]+', text)

def parse_local_email(file_path):
    with open(file_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    # ---------- HEADERS ----------
    headers = {
        "raw_subject": msg.get("Subject", ""),
        "authentication_results": msg.get("Authentication-Results", ""),
        "received_count": len(msg.get_all("Received", [])),
        "message_id": msg.get("Message-ID", ""),
        "list_unsubscribe": msg.get("List-Unsubscribe", ""),
        "raw_headers": dict(msg.items())
    }

    # ---------- META ----------
    def parse_address(addr):
        if not addr:
            return {"display_name": "", "address": "", "domain": ""}
        name, email_addr = email.utils.parseaddr(addr)
        domain = email_addr.split("@")[-1] if "@" in email_addr else ""
        return {
            "display_name": name,
            "address": email_addr,
            "domain": domain
        }

    meta = {
        "from": parse_address(msg.get("From")),
        "reply_to": [parse_address(a) for a in msg.get_all("Reply-To", [])] if msg.get_all("Reply-To") else [],
        "return_path": parse_address(msg.get("Return-Path")),
        "date": {
            "raw": msg.get("Date", ""),
            "parsed": ""
        }
    }

    # Date parsing
    try:
        dt = email.utils.parsedate_to_datetime(msg.get("Date"))
        meta["date"]["parsed"] = dt.isoformat()
    except:
        meta["date"]["parsed"] = ""

    # ---------- AUTH ----------
    auth = {
        "spf": "",
        "dkim": "",
        "dmarc": ""
    }

    auth_res = msg.get("Authentication-Results", "")
    if auth_res:
        if "spf=" in auth_res:
            auth["spf"] = auth_res.split("spf=")[1].split()[0]
        if "dkim=" in auth_res:
            auth["dkim"] = auth_res.split("dkim=")[1].split()[0]
        if "dmarc=" in auth_res:
            auth["dmarc"] = auth_res.split("dmarc=")[1].split()[0]

    # ---------- ROUTING ----------
    received_headers = msg.get_all("Received", []) or []
    routing = {
        "received": received_headers,
        "hops": len(received_headers)
    }

    # ---------- CONTENT ----------
    body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    body += part.get_content()
                except:
                    pass
            elif part.get_filename():
                attachments.append({
                    "filename": part.get_filename(),
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b"")
                })
    else:
        body = msg.get_content()

    urls = extract_urls(body)

    # ---------- FINAL STRUCTURE ----------
    parsed = {
        "headers": headers,
        "meta": meta,
        "auth": auth,
        "routing": routing,
        "content": body,
        "urls": urls,
        "attachments": attachments
    }

    # ---------- WRITE parsed.json ----------
    os.makedirs("/results", exist_ok=True)
    with open("/results/parsed.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=4, ensure_ascii=False)

    return parsed
