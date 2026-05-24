"""
Lightweight keyword-based email classifier.
No API calls — runs instantly on every email.
"""

AMT_KEYWORDS = {
    "camera", "drone", "lens", "audio", "lighting", "broadcast", "media", "video",
    "quote", "rfq", "inquiry", "enquiry", "proposal", "budget", "invoice", "order",
    "shipment", "delivery", "stock", "inventory", "purchase", "procurement", "po",
    "sony", "dji", "red", "arri", "zeiss", "sennheiser", "profoto", "atomos",
    "repair", "service", "warranty", "maintenance", "fault", "broken",
    "vat", "payment", "overdue", "receivable", "finance", "credit",
    "amt", "advanced media", "equipment", "av ", "production", "gimbal",
    "microphone", "camcorder", "tripod", "studio", "film", "cinema",
    "teradek", "blackmagic", "canon", "nikon", "fujifilm", "panasonic",
    "stabilizer", "monitor", "switcher", "encoder", "transmitter", "receiver",
    "aputure", "astera", "cooke", "sachtler", "manfrotto", "smallrig",
}

DEPT_KEYWORDS = {
    "sales": {
        "quote", "rfq", "inquiry", "enquiry", "price", "pricing", "buy", "purchase",
        "availability", "stock", "product", "model", "budget", "proposal", "catalog",
        "demo", "specification", "spec", "recommend", "compare", "offer",
        "camera", "drone", "lens", "gimbal", "audio", "lighting", "kit",
        "package", "bundle", "configuration", "solution",
    },
    "distribution": {
        "shipment", "shipping", "delivery", "customs", "freight", "logistics",
        "eta", "tracking", "dispatch", "cargo", "warehouse", "order status",
        "delayed", "arrived", "transit", "consignment", "clearance", "import",
        "export", "forwarder", "awb", "bl", "airway",
    },
    "finance": {
        "invoice", "payment", "overdue", "vat", "tax", "balance", "receivable",
        "credit", "outstanding", "billing", "statement", "remittance", "transfer",
        "bank", "amount due", "proforma", "receipt", "finance", "accounting",
        "due date", "past due", "collection",
    },
    "service": {
        "repair", "warranty", "broken", "fault", "malfunction", "maintenance",
        "ticket", "support", "technical", "issue", "problem", "not working",
        "damaged", "fix", "replacement", "rma", "return", "defective",
        "under warranty", "out of warranty", "service request",
    },
}


# Keywords whose presence almost always signals a marketing/automated email
_MARKETING_SIGNALS = {"unsubscribe", "opt-out", "opt out", "no hard feelings",
                       "you received this email to let you know about important changes",
                       "terms and conditions apply", "©", "© 20"}


def is_amt_relevant(subject: str, body: str, from_addr: str = "") -> bool:
    # Block noreply/no-reply senders — never a real business inquiry
    if from_addr:
        fa = from_addr.lower()
        if "noreply" in fa or "no-reply" in fa:
            return False

    # Block marketing / newsletter / automated emails
    body_lower = body[:2000].lower()
    if any(sig in body_lower for sig in _MARKETING_SIGNALS):
        return False

    text = (subject + " " + body[:1200]).lower()
    score = sum(1 for kw in AMT_KEYWORDS if kw in text)
    return score >= 2


def classify_dept(subject: str, body: str) -> str:
    text = (subject + " " + body[:800]).lower()
    scores = {dept: sum(1 for kw in kws if kw in text) for dept, kws in DEPT_KEYWORDS.items()}
    best_dept  = max(scores, key=scores.get)
    best_score = scores[best_dept]
    return best_dept if best_score > 0 else "sales"
