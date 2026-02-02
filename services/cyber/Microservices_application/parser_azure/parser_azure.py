"""
Parser Azure v4.3 - Texte seul en email_body + URLs depuis HTML
"""

from flask import Flask, request, jsonify
import os, sys, email, re, quopri
from email import policy
from email.parser import BytesParser
from pathlib import Path

sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)

# ---------------------------------------------------------
# URL extraction
# ---------------------------------------------------------
def extract_urls(text):
    if not text:
        return []
    urls = re.findall(r'https?://[^\s<>"\')]+', text)
    return list(set(urls))

def extract_domain(url):
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except:
        return ""

# ---------------------------------------------------------
# Attachments helpers
# ---------------------------------------------------------
def get_file_extension(filename):
    return Path(filename).suffix.lstrip('.').lower() if filename else ""

def is_dangerous_extension(ext):
    return ext.lower() in ['exe','bat','cmd','com','pif','scr','vbs','js','jar','msi']

# ---------------------------------------------------------
# HTML DECODER (quoted-printable)
# ---------------------------------------------------------
def decode_html_part(raw_html):
    try:
        decoded = quopri.decodestring(raw_html).decode("utf-8", errors="ignore")
        decoded = decoded.replace("=\n", "")   # soft line breaks
        decoded = decoded.replace("=3D", "=")  # quoted-printable "="
        return decoded
    except:
        return ""

# ---------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------
def parse_email_file(file_path, analysis_id):
    with open(file_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    # -------------------------------
    # HEADERS
    # -------------------------------
    email_subject = msg.get("Subject", "")
    sender_from = msg.get("From", "")
    display_name, email_sender = email.utils.parseaddr(sender_from)

    reply_to_header = msg.get("Reply-To", "")
    _, reply_to = email.utils.parseaddr(reply_to_header) if reply_to_header else ("", "")

    return_path = msg.get("Return-Path", "").strip('<>').strip()

    try:
        email_date = email.utils.parsedate_to_datetime(msg.get("Date"))
    except:
        email_date = None

    # -------------------------------
    # AUTH RESULTS
    # -------------------------------
    auth_spf = auth_dkim = auth_dmarc = "unknown"
    auth_results = msg.get("Authentication-Results", "").lower()

    if "spf=pass" in auth_results:
        auth_spf = "pass"
    elif "spf=fail" in auth_results:
        auth_spf = "fail"

    if "dkim=pass" in auth_results:
        auth_dkim = "pass"
    elif "dkim=fail" in auth_results:
        auth_dkim = "fail"

    if "dmarc=pass" in auth_results:
        auth_dmarc = "pass"
    elif "dmarc=fail" in auth_results:
        auth_dmarc = "fail"

    # -------------------------------
    # IP extraction
    # -------------------------------
    sender_ip = None
    ip_regex = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'

    headers_to_scan = []
    headers_to_scan += msg.get_all("Received", []) or []

    for h in ["Authentication-Results", "ARC-Authentication-Results", "Received-SPF"]:
        val = msg.get(h)
        if val:
            headers_to_scan.append(val)

    rp = msg.get("Return-Path")
    if rp:
        headers_to_scan.append(rp)

    all_ips = []
    for h in headers_to_scan:
        all_ips.extend(re.findall(ip_regex, h))

    def is_public(ip):
        return not (
            ip.startswith("10.") or
            ip.startswith("192.168.") or
            (ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31)
        )

    public_ips = [ip for ip in all_ips if is_public(ip)]
    if public_ips:
        sender_ip = public_ips[0]

    # -------------------------------
    # BODY + ATTACHMENTS
    # -------------------------------
    body_text = ""        # ce qui ira dans email_body
    html_for_urls = ""    # HTML décodé uniquement pour l'extraction d'URLs
    attachments_list = []

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()

            # ---- TEXT/PLAIN ----
            if ctype == "text/plain":
                try:
                    body_text += part.get_content()
                except:
                    pass

            # ---- TEXT/HTML (pour URLs uniquement) ----
            elif ctype == "text/html":
                raw_html = part.get_payload(decode=True)
                if raw_html:
                    decoded_html = decode_html_part(raw_html)
                    html_for_urls += "\n" + decoded_html

            # ---- ATTACHMENTS ----
            elif part.get_filename():
                fname = part.get_filename()
                ext = get_file_extension(fname)
                try:
                    size = len(part.get_payload(decode=True) or b"")
                except:
                    size = 0

                attachments_list.append({
                    "filename": fname,
                    "extension": ext,
                    "content_type": ctype,
                    "size": size,
                    "is_dangerous": is_dangerous_extension(ext)
                })
    else:
        # Cas non multipart (rare mais possible)
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            try:
                body_text = msg.get_content()
            except:
                body_text = ""
        elif ctype == "text/html":
            raw_html = msg.get_payload(decode=True)
            if raw_html:
                html_for_urls = decode_html_part(raw_html)

    # -------------------------------
    # URL extraction (texte + HTML)
    # -------------------------------
    urls_source = (body_text or "") + "\n" + (html_for_urls or "")
    urls_list = extract_urls(urls_source)
    urls_list = list(set(urls_list))

    urls_with_domains = [
        {"url": u, "domain": extract_domain(u), "is_suspicious": False}
        for u in urls_list
    ]

    return {
        "analysis_id": analysis_id,
        "email_subject": email_subject,
        "email_sender": email_sender,
        "email_date": email_date,
        "display_name": display_name,
        "reply_to": reply_to,
        "return_path": return_path,
        "auth_spf": auth_spf,
        "auth_dkim": auth_dkim,
        "auth_dmarc": auth_dmarc,
        "sender_ip": sender_ip,
        "sender_country": None,
        "email_body": body_text.strip(),  # ✅ uniquement le corps texte
        "attachments": attachments_list,
        "urls": urls_with_domains
    }

# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------
@app.post("/process/<int:analysis_id>")
def process_one(analysis_id):
    try:
        db = get_db()
        analyses = db.get_pending_analyses(1000)
        analysis = next((a for a in analyses if a['id'] == analysis_id), None)

        if not analysis:
            complete = db.get_complete_analysis(analysis_id)
            if not complete:
                return jsonify({"error": "Introuvable"}), 404
            file_path = complete['raw_file_path']
        else:
            file_path = analysis['raw_file_path']

        parsed = parse_email_file(file_path, analysis_id)

        email_info = {k: parsed[k] for k in [
            'email_subject', 'email_sender', 'email_date', 'display_name',
            'reply_to', 'return_path', 'sender_ip', 'sender_country',
            'auth_spf', 'auth_dkim', 'auth_dmarc', 'email_body'
        ]}

        db.update_analysis_email_info(analysis_id, email_info)

        if parsed['attachments']:
            db.add_attachments(analysis_id, parsed['attachments'])

        if parsed['urls']:
            db.add_urls(analysis_id, parsed['urls'])

        db.update_status(analysis_id, "processing")

        return jsonify({"analysis_id": analysis_id, "status": "success"})

    except Exception as e:
        print("🔥 ERREUR PARSER :", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
