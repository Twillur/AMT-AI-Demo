import imaplib, email, os, re
from email.header import decode_header


def _decode_str(s):
    if s is None:
        return ""
    parts = decode_header(s)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(chunk))
    return " ".join(out).strip()


def _get_body(msg):
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct  = part.get_content_type()
            cd  = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if ct == "text/plain" and not plain:
                plain = text
            elif ct == "text/html" and not html:
                html = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html = text
            else:
                plain = text

    if plain:
        return plain.strip()
    if html:
        # Strip tags for plain-text body
        cleaned = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL)
        cleaned = re.sub(r"<script[^>]*>.*?</script>", " ", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
    return ""


def _parse_from(raw):
    raw = _decode_str(raw)
    m = re.match(r'^"?([^"<]*?)"?\s*<([^>]+)>', raw)
    if m:
        return m.group(1).strip() or m.group(2).strip(), m.group(2).strip()
    return raw.strip(), raw.strip()


def _connect():
    addr = os.getenv("GMAIL_ADDRESS", "").strip()
    pwd  = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    if not addr or not pwd:
        raise ValueError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD are not set in .env")
    m = imaplib.IMAP4_SSL("imap.gmail.com")
    m.login(addr, pwd)
    return m


def fetch_inbox(max_count=30):
    mail = _connect()
    mail.select("INBOX")

    # Use UID-based search — UIDs are stable across sessions
    _, data = mail.uid("search", None, "ALL")
    all_uids = data[0].split()
    uids = all_uids[-max_count:][::-1]  # most recent first

    if not uids:
        mail.logout()
        return []

    uid_list = b",".join(uids)

    # Batch-fetch FLAGS
    _, flag_data = mail.uid("fetch", uid_list, "(FLAGS)")
    flags_map = {}
    for item in flag_data:
        if isinstance(item, tuple):
            raw = item[1].decode() if isinstance(item[1], bytes) else str(item[1])
            m = re.search(r"UID (\d+).*?FLAGS \(([^)]*)\)", raw)
            if m:
                flags_map[m.group(1)] = m.group(2)

    messages = []
    for uid in uids:
        uid_str = uid.decode()
        _, raw_data = mail.uid("fetch", uid, "(RFC822)")
        if not raw_data or not raw_data[0]:
            continue
        msg = email.message_from_bytes(raw_data[0][1])
        from_name, from_addr = _parse_from(msg.get("From", ""))
        subject  = _decode_str(msg.get("Subject", "(no subject)"))
        date_raw = msg.get("Date", "")
        body     = _get_body(msg)
        unread   = "\\Seen" not in flags_map.get(uid_str, "")

        messages.append({
            "id":        uid_str,
            "subject":   subject,
            "from_name": from_name,
            "from_addr": from_addr,
            "date":      date_raw,
            "body":      body,
            "preview":   body[:200].replace("\n", " "),
            "unread":    unread,
        })

    mail.logout()
    return messages


def trash_mail(uid: str):
    """Move an email to Gmail Trash by UID."""
    mail = _connect()
    mail.select("INBOX")
    uid_bytes = uid.encode() if isinstance(uid, str) else uid
    mail.uid("copy", uid_bytes, "[Gmail]/Trash")
    mail.uid("store", uid_bytes, "+FLAGS", "\\Deleted")
    mail.expunge()
    mail.logout()
