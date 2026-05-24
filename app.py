import os, sqlite3, json as _json, threading, time as _time
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# ── LangSmith tracing (auto-traces all LangChain calls) ──────────────────────
if os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGCHAIN_API_KEY") != "PASTE_YOUR_LANGSMITH_KEY_HERE":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "AMT-Demo")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "amt-demo-2026")

_ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "1234")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

@app.route("/login")
def login_page():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    if data.get("username") == _ADMIN_USER and data.get("password") == _ADMIN_PASS:
        session["logged_in"] = True
        return jsonify({"ok": True, "redirect": "/"})
    return jsonify({"ok": False}), 401

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True, "redirect": "/login"})

_DB = os.path.join(os.path.dirname(__file__), "db", "amt.db")

def _init_chat_log():
    con = sqlite3.connect(_DB)
    con.execute('''CREATE TABLE IF NOT EXISTS chat_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        dept        TEXT NOT NULL,
        user_msg    TEXT NOT NULL,
        ai_response TEXT NOT NULL,
        tools_json  TEXT DEFAULT '[]',
        tokens_json TEXT DEFAULT '{}',
        ts          TEXT DEFAULT (datetime('now'))
    )''')
    con.commit(); con.close()

def _save_chat(dept, user_msg, ai_response, tools, tokens):
    con = sqlite3.connect(_DB)
    con.execute(
        "INSERT INTO chat_log (dept,user_msg,ai_response,tools_json,tokens_json) VALUES (?,?,?,?,?)",
        (dept, user_msg, ai_response, _json.dumps(tools), _json.dumps(tokens))
    )
    con.commit(); con.close()

_init_chat_log()

def _auto_seed():
    """Seed the database if the business tables are empty or missing."""
    try:
        con = sqlite3.connect(_DB)
        n = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        con.close()
        if n > 0:
            return  # already seeded
    except Exception:
        pass  # table doesn't exist yet
    import subprocess, sys
    seed = os.path.join(os.path.dirname(__file__), "db", "seed.py")
    print("[AMT] Database empty — seeding now...")
    subprocess.run([sys.executable, seed], check=True)
    print("[AMT] Database ready.")

_auto_seed()

from agents import langgraph_flow
from agents import sales as sales_agent
from agents import reports as report_gen
from agents.db_utils import query


def get_stats():
    sales_stats = {
        "products": query("SELECT COUNT(*) AS n FROM products")[0]["n"],
        "orders_active": query("SELECT COUNT(*) AS n FROM orders WHERE status IN ('pending','confirmed','shipped')")[0]["n"],
        "top_brand": query("SELECT brand, COUNT(*) AS n FROM products GROUP BY brand ORDER BY n DESC LIMIT 1")[0]["brand"],
        "brands_in_stock": query("SELECT COUNT(DISTINCT p.brand) AS n FROM products p JOIN inventory i ON i.product_id=p.id WHERE (i.qty_on_hand-i.qty_reserved)>0")[0]["n"],
    }
    dist_stats = {
        "delayed": query("SELECT COUNT(*) AS n FROM shipments WHERE status IN ('delayed','customs')")[0]["n"],
        "in_transit": query("SELECT COUNT(*) AS n FROM shipments WHERE status='in_transit'")[0]["n"],
        "low_stock": query("SELECT COUNT(*) AS n FROM inventory WHERE (qty_on_hand - qty_reserved) <= 3")[0]["n"],
    }
    fin_stats = {
        "overdue": query("SELECT COUNT(*) AS n FROM invoices WHERE status='overdue'")[0]["n"],
        "outstanding_aed": query("SELECT COALESCE(SUM(amount_aed),0) AS n FROM invoices WHERE status IN ('unpaid','overdue')")[0]["n"],
        "unpaid": query("SELECT COUNT(*) AS n FROM invoices WHERE status='unpaid'")[0]["n"],
        "paid": query("SELECT COUNT(*) AS n FROM invoices WHERE status='paid'")[0]["n"],
    }
    svc_stats = {
        "open": query("SELECT COUNT(*) AS n FROM service_tickets WHERE status='open'")[0]["n"],
        "in_repair": query("SELECT COUNT(*) AS n FROM service_tickets WHERE status IN ('in_repair','diagnosed','awaiting_parts')")[0]["n"],
        "ready": query("SELECT COUNT(*) AS n FROM service_tickets WHERE status='ready'")[0]["n"],
    }
    return {"sales": sales_stats, "distribution": dist_stats, "finance": fin_stats, "service": svc_stats}


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/overview")
@login_required
def overview():
    return render_template("overview.html")


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json()
    department = data.get("department", "sales")
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "No message provided"}), 400
    if department not in ("sales", "distribution", "finance", "service", "auto"):
        return jsonify({"error": "Unknown department"}), 400

    history_key = f"history_{department}"
    history = session.get(history_key, [])

    try:
        response_text, tools_used, tokens = langgraph_flow.run(department, message, history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response_text})
    if len(history) > 20:
        history = history[-20:]
    session[history_key] = history

    _save_chat(department, message, response_text, tools_used, tokens)

    return jsonify({"response": response_text, "tools": tools_used, "tokens": tokens})


@app.route("/api/stats")
@login_required
def stats():
    return jsonify(get_stats())


_DEPT_CTX = {
    "distribution": {
        "role": "Distribution & Logistics Coordinator", "email": "logistics@amt.tv",
        "accent": "#10d97a", "header": "Logistics Response",
        "instructions": (
            "Acknowledge the specific issue (customs hold, shipment update, PO status, ETA etc.). "
            "State exactly what action AMT will take. Reference shipment refs, AWB, PO numbers from the email. "
            "Provide realistic timelines. Keep it factual and action-oriented."
        ),
    },
    "finance": {
        "role": "Finance & Accounts Team", "email": "finance@amt.tv",
        "accent": "#f0a500", "header": "Finance Response",
        "instructions": (
            "Acknowledge payment receipt or invoice/statement query. "
            "Confirm next steps (receipt, VAT-compliant tax invoice, TRN certificate, updated statement). "
            "Reference invoice refs, amounts, and payment details from the email. Mention 1-2 business day processing."
        ),
    },
    "service": {
        "role": "AMT Service Center", "email": "service@amt.tv",
        "accent": "#a855f7", "header": "Service Acknowledgment",
        "instructions": (
            "Confirm receipt of the service/repair request and assign a ticket reference number (format SVC-2026-XXX). "
            "Address warranty coverage — if purchase was within the last 24 months and is a manufacturing defect, confirm it is covered. "
            "Provide turnaround estimate (standard 5-7 business days; mention you can prioritise if there is a production deadline). "
            "Address loan unit request (subject to availability, team will confirm within 24h). "
            "Give drop-off instructions for the Dubai service center. "
            "Be reassuring and professional. Reference the specific product and issue."
        ),
    },
    "sales": {
        "role": "Sales Team", "email": "sales@amt.tv",
        "accent": "#3b7eff", "header": "Sales Response",
        "instructions": (
            "Respond to the sales inquiry professionally. Provide relevant product/service information. "
            "Offer to arrange a demo or quote if appropriate."
        ),
    },
}

def _build_response_html(from_name: str, data: dict, ctx: dict) -> str:
    paras = "".join(
        f'<p style="margin:0 0 14px;font-size:14px;color:#444;line-height:1.65">{p}</p>'
        for p in data.get("paragraphs", [])
    )
    actions = data.get("action_items", [])
    actions_html = ""
    if actions:
        items = "".join(f'<li style="margin-bottom:6px;color:#444;font-size:14px">{a}</li>' for a in actions)
        actions_html = f'''<div style="background:#f8f9fa;border-left:3px solid {ctx["accent"]};padding:14px 18px;margin:16px 0;border-radius:0 6px 6px 0">
            <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:#999;letter-spacing:1px;text-transform:uppercase">We will</p>
            <ul style="margin:0;padding-left:20px">{items}</ul>
        </div>'''
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:0 auto;padding:20px">
  <div style="background:#0d1b2a;padding:20px 28px;border-radius:8px 8px 0 0">
    <div style="color:{ctx['accent']};font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase">Advanced Media Trading LLC</div>
    <div style="color:#fff;font-size:18px;font-weight:700;margin-top:4px">{ctx['header']}</div>
  </div>
  <div style="background:#fff;border:1px solid #e0e0e0;border-top:none;padding:28px;border-radius:0 0 8px 8px">
    <p style="margin:0 0 16px;font-size:15px">{data.get('greeting', f'Dear {from_name},')}</p>
    {paras}{actions_html}
    <p style="margin:28px 0 0;font-size:14px">{data.get('closing','Kind regards,')}<br>
    <strong>{data.get('sender_name', ctx['role'])}</strong><br>
    <span style="color:#888;font-size:12px">Advanced Media Trading LLC &nbsp;|&nbsp; {data.get('footer_email', ctx['email'])} &nbsp;|&nbsp; {data.get('footer_phone', '+971 4 447 6000')}</span></p>
  </div>
</body></html>"""


@app.route("/api/generate-response", methods=["POST"])
@login_required
def generate_response():
    from openai import OpenAI as _OAI
    data = request.get_json()
    dept       = data.get("dept", "sales")
    from_name  = data.get("from_name", "Customer")
    from_addr  = data.get("from", "")
    subject    = data.get("subject", "")
    body       = data.get("body", "")
    refinement = data.get("refinement", "").strip()   # optional: user instruction to refine

    ctx = _DEPT_CTX.get(dept, _DEPT_CTX["sales"])
    base_system = f"""You are the {ctx['role']} at Advanced Media Trading LLC (AMT), Dubai — MENA's largest professional AV distributor. Authorized DJI distributor and dealer for Sony, RED, Sennheiser, Zeiss, and 50+ professional AV brands.

Return ONLY valid JSON:
{{"greeting":"Dear [name],","paragraphs":["para1","para2"],"action_items":["action1"],"closing":"Kind regards,","sender_name":"{ctx['role']}","footer_email":"{ctx['email']}","footer_phone":"+971 4 447 6000"}}
Max 3-4 paragraphs. Action items = short bullet phrases. You may update footer_email and footer_phone if the user's refinement instruction asks to change contact details."""

    if refinement:
        system = base_system + f"\n\nThe user wants to refine the draft with this instruction: \"{refinement}\". Apply it faithfully."
        user_msg = f"Original email:\nSubject: {subject}\nFrom: {from_name} <{from_addr}>\n\n{body}\n\n---\nRefinement instruction: {refinement}"
    else:
        system = base_system + f"\n\nDraft a professional response. Instructions: {ctx['instructions']}"
        user_msg = f"Subject: {subject}\nFrom: {from_name} <{from_addr}>\n\n{body}"

    _client = _OAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        resp = _client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        resp_data = _json.loads(resp.choices[0].message.content)
        html = _build_response_html(from_name, resp_data, ctx)
        return jsonify({"html_response": html, "dept_label": ctx["header"], "ok": True})
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/api/rfq", methods=["POST"])
@login_required
def rfq():
    data = request.get_json()
    from_email = data.get("from", "unknown@example.com")
    from_name  = data.get("from_name", "Customer")
    subject    = data.get("subject", "Quote Request")
    body       = data.get("body", "")
    if not body:
        return jsonify({"error": "No email body"}), 400
    try:
        result = sales_agent.run_rfq(from_email, from_name, subject, body)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/send_reply", methods=["POST"])
@login_required
def send_reply():
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    data = request.get_json()
    to_addr  = data.get("to", "")
    to_name   = data.get("to_name", "")
    subject   = data.get("subject", "Re: Your Inquiry")
    html_body = data.get("html_body", "")
    cc_addrs  = [a.strip() for a in data.get("cc", "").split(",") if a.strip()]
    bcc_addrs = [a.strip() for a in data.get("bcc", "").split(",") if a.strip()]
    if not to_addr:
        return jsonify({"error": "No recipient"}), 400

    gmail_addr = os.getenv("GMAIL_ADDRESS")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    if not gmail_addr or not gmail_pass:
        return jsonify({"error": "Gmail not configured", "ok": False}), 503

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"AMT <{gmail_addr}>"
        msg["To"]      = f"{to_name} <{to_addr}>" if to_name else to_addr
        if cc_addrs:
            msg["Cc"] = ", ".join(cc_addrs)
        msg.attach(MIMEText(html_body, "html"))
        all_recipients = [to_addr] + cc_addrs + bcc_addrs
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_addr, gmail_pass)
            server.sendmail(gmail_addr, all_recipients, msg.as_string())
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/api/delete-mail", methods=["POST"])
@login_required
def delete_mail():
    from agents.gmail_imap import trash_mail
    data = request.get_json()
    uid = str(data.get("uid", "")).strip()
    if not uid:
        return jsonify({"error": "No uid provided"}), 400
    try:
        trash_mail(uid)
        # Remove from in-memory cache immediately so the inbox reflects it
        if _mail_cache.get("messages"):
            _mail_cache["messages"] = [m for m in _mail_cache["messages"] if str(m.get("id")) != uid]
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/embeddings")
@login_required
def embeddings_viz():
    return render_template("embeddings.html")


_emb_cache = {"ts": 0.0, "data": None}
_EMB_TTL = 300  # seconds

@app.route("/api/embeddings-data")
@login_required
def embeddings_data():
    import time, numpy as np
    from sklearn.manifold import TSNE
    import chromadb as _chroma

    if _emb_cache["data"] and (time.time() - _emb_cache["ts"]) < _EMB_TTL:
        return jsonify(_emb_cache["data"])

    db_dir = os.path.join(os.path.dirname(__file__), "db", "chroma")
    client = _chroma.PersistentClient(path=db_dir)
    try:
        col = client.get_collection("amt_products_v2")
    except Exception:
        return jsonify([])

    result = col.get(include=["embeddings", "metadatas", "documents"])
    embeddings = np.array(result["embeddings"], dtype=np.float32)
    metadatas  = result["metadatas"]
    documents  = result["documents"]
    n = len(embeddings)
    if n == 0:
        return jsonify([])

    perplexity = min(30, max(5, n - 1))
    coords = TSNE(n_components=2, perplexity=perplexity,
                  random_state=42, max_iter=1000, verbose=0).fit_transform(embeddings)

    points = []
    for i in range(n):
        m = metadatas[i] or {}
        points.append({
            "x":        float(coords[i, 0]),
            "y":        float(coords[i, 1]),
            "brand":    m.get("brand", ""),
            "model":    m.get("model", ""),
            "category": m.get("category", ""),
            "price":    m.get("price_aed", 0),
            "desc":     (documents[i] or "")[:200],
        })

    _emb_cache["data"] = points
    _emb_cache["ts"]   = time.time()
    return jsonify(points)


@app.route("/domains")
@login_required
def domains_page():
    return render_template("domains.html")


@app.route("/api/domains")
@login_required
def domains_api():
    from agents.domains_config import get_domains_payload
    return jsonify(get_domains_payload())


@app.route("/api/report/distribution")
@login_required
def report_distribution():
    return jsonify({"html": report_gen.distribution_briefing_html()})


@app.route("/api/report/finance")
@login_required
def report_finance():
    return jsonify({"html": report_gen.finance_overdue_html()})


@app.route("/mail")
@login_required
def mail_page():
    return render_template("mail.html")


# ── Background mail cache ─────────────────────────────────────────────────────
_mail_cache = {"data": None, "error": None, "setup_required": False, "ts": 0.0}
_MAIL_TTL = 300  # refresh every 5 minutes

def _fetch_and_cache_mail():
    try:
        from agents.gmail_imap import fetch_inbox
        from agents.email_classifier import is_amt_relevant, classify_dept
        raw = fetch_inbox(max_count=60)
        messages = []
        for m in raw:
            if not is_amt_relevant(m["subject"], m["body"], m.get("from_addr", "")):
                continue
            m["dept"] = classify_dept(m["subject"], m["body"])
            messages.append(m)
        _mail_cache["data"] = messages
        _mail_cache["error"] = None
        _mail_cache["setup_required"] = False
        _mail_cache["ts"] = _time.time()
    except ValueError as e:
        _mail_cache["error"] = str(e)
        _mail_cache["setup_required"] = True
    except Exception as e:
        _mail_cache["error"] = str(e)
        _mail_cache["setup_required"] = False

def _mail_bg_loop():
    while True:
        _fetch_and_cache_mail()
        _time.sleep(_MAIL_TTL)

threading.Thread(target=_mail_bg_loop, daemon=True).start()


@app.route("/api/mail")
@login_required
def mail_api():
    force = request.args.get("force") == "1"
    if force:
        _fetch_and_cache_mail()
    if _mail_cache["error"]:
        return jsonify({"error": _mail_cache["error"], "ok": False,
                        "setup_required": _mail_cache["setup_required"]}), 503
    if _mail_cache["data"] is None:
        # Still loading on first boot — fetch synchronously
        _fetch_and_cache_mail()
        if _mail_cache["error"]:
            return jsonify({"error": _mail_cache["error"], "ok": False,
                            "setup_required": _mail_cache["setup_required"]}), 503
    return jsonify({"messages": _mail_cache["data"], "ok": True})


@app.route("/api/metric-detail/<metric>")
@login_required
def metric_detail(metric):
    _queries = {
        "products":      "SELECT brand, model, category, price_aed, sku FROM products ORDER BY brand, model",
        "active_orders": "SELECT o.order_ref, c.name, c.company, o.order_date, o.status, o.total_aed FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.status IN ('pending','confirmed','shipped') ORDER BY o.order_date DESC",
        "brands_stock":  "SELECT p.brand, SUM(i.qty_on_hand-i.qty_reserved) AS qty_available, SUM(i.qty_on_hand) AS qty_on_hand, MAX(i.reorder_point) AS reorder_point FROM products p JOIN inventory i ON i.product_id=p.id GROUP BY p.brand ORDER BY qty_available DESC",
        "in_transit":    "SELECT s.shipment_ref, s.supplier, s.carrier, s.status, s.eta FROM shipments s WHERE s.status='in_transit' ORDER BY s.eta",
        "delayed":       "SELECT s.shipment_ref, s.supplier, s.carrier, s.status, s.eta FROM shipments s WHERE s.status IN ('delayed','customs') ORDER BY s.eta",
        "customs":       "SELECT s.shipment_ref, s.supplier, s.carrier, s.status, s.eta FROM shipments s WHERE s.status='customs'",
        "low_stock":     "SELECT p.brand, p.model, SUM(i.qty_on_hand-i.qty_reserved) AS qty_available, MAX(i.reorder_point) AS reorder_point FROM products p JOIN inventory i ON i.product_id=p.id GROUP BY p.id HAVING qty_available <= reorder_point ORDER BY qty_available",
        "overdue":       "SELECT inv.invoice_ref, c.name, c.company, inv.amount_aed, inv.due_date FROM invoices inv JOIN customers c ON c.id=inv.customer_id WHERE inv.status='overdue' ORDER BY inv.due_date",
        "unpaid":        "SELECT inv.invoice_ref, c.name, c.company, inv.amount_aed, inv.due_date FROM invoices inv JOIN customers c ON c.id=inv.customer_id WHERE inv.status='unpaid' ORDER BY inv.due_date",
        "open_tickets":  "SELECT t.ticket_ref, c.name, p.model, t.issue_description, t.received_date FROM service_tickets t JOIN customers c ON c.id=t.customer_id JOIN products p ON p.id=t.product_id WHERE t.status='open' ORDER BY t.received_date DESC",
        "in_repair":     "SELECT t.ticket_ref, c.name, p.model, t.status, t.issue_description FROM service_tickets t JOIN customers c ON c.id=t.customer_id JOIN products p ON p.id=t.product_id WHERE t.status IN ('in_repair','diagnosed','awaiting_parts') ORDER BY t.received_date",
        "ready_tickets": "SELECT t.ticket_ref, c.name, p.model, t.status FROM service_tickets t JOIN customers c ON c.id=t.customer_id JOIN products p ON p.id=t.product_id WHERE t.status='ready'",
        "paid_invoices": "SELECT inv.invoice_ref, c.name, c.company, inv.amount_aed, inv.due_date FROM invoices inv JOIN customers c ON c.id=inv.customer_id WHERE inv.status='paid' ORDER BY inv.due_date DESC",
    }
    if metric not in _queries:
        return jsonify({"error": "Unknown metric"}), 404
    return jsonify(query(_queries[metric]))


@app.route("/insights")
@login_required
def insights_page():
    return render_template("insights.html")


@app.route("/api/insights-detail/<string:chart>/<path:key>")
@login_required
def insights_detail(chart, key):
    _queries = {
        'invoice-status': (
            "SELECT inv.invoice_ref, c.name, c.company, inv.amount_aed, inv.due_date FROM invoices inv JOIN customers c ON c.id=inv.customer_id WHERE inv.status=? ORDER BY inv.amount_aed DESC",
            ['invoice_ref','name','company','amount_aed','due_date'], ['Invoice','Customer','Company','Amount (AED)','Due Date']
        ),
        'stock-category': (
            "SELECT p.brand, p.model, SUM(i.qty_on_hand-i.qty_reserved) AS available, SUM(i.qty_on_hand) AS qty_on_hand, MAX(i.reorder_point) AS reorder_point FROM products p JOIN inventory i ON i.product_id=p.id WHERE p.category=? GROUP BY p.id ORDER BY available DESC",
            ['brand','model','available','qty_on_hand','reorder_point'], ['Brand','Model','Available','On Hand','Reorder Pt']
        ),
        'brand-orders': (
            "SELECT o.order_ref, c.name, c.company, o.order_date, o.status, oi.qty FROM order_items oi JOIN products p ON p.id=oi.product_id JOIN orders o ON o.id=oi.order_id JOIN customers c ON c.id=o.customer_id WHERE p.brand=? ORDER BY o.order_date DESC",
            ['order_ref','name','company','order_date','status','qty'], ['Order','Customer','Company','Date','Status','Qty']
        ),
        'shipment-status': (
            "SELECT s.shipment_ref, s.supplier, s.carrier, s.status, s.eta FROM shipments s WHERE s.status=? ORDER BY s.eta",
            ['shipment_ref','supplier','carrier','status','eta'], ['Shipment','Supplier','Carrier','Status','ETA']
        ),
        'order-status': (
            "SELECT o.order_ref, c.name, c.company, o.order_date, o.total_aed FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.status=? ORDER BY o.order_date DESC",
            ['order_ref','name','company','order_date','total_aed'], ['Order','Customer','Company','Date','Value (AED)']
        ),
        'ticket-status': (
            "SELECT t.ticket_ref, c.name, p.model, t.status, t.issue_description, t.received_date FROM service_tickets t JOIN customers c ON c.id=t.customer_id JOIN products p ON p.id=t.product_id WHERE t.status=? ORDER BY t.received_date DESC",
            ['ticket_ref','name','model','status','issue_description','received_date'], ['Ticket','Customer','Product','Status','Issue','Date']
        ),
        'country-orders': (
            "SELECT o.order_ref, c.name, c.company, o.order_date, o.status, o.total_aed FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.country=? ORDER BY o.order_date DESC",
            ['order_ref','name','company','order_date','status','total_aed'], ['Order','Customer','Company','Date','Status','Value (AED)']
        ),
    }
    if chart not in _queries:
        return jsonify({"error": "Unknown chart"}), 404
    sql, fields, labels = _queries[chart]
    try:
        con = sqlite3.connect(_DB)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(sql, [key]).fetchall()]
        con.close()
        return jsonify({"rows": rows, "fields": fields, "labels": labels})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/draft-reorder-email", methods=["POST"])
@login_required
def draft_reorder_email():
    from openai import OpenAI as _OAI
    data = request.get_json()
    brand        = data.get("brand", "")
    model        = data.get("model", "")
    qty_available = int(data.get("qty_available", 0))
    reorder_point = int(data.get("reorder_point", 0))

    # Pull real product details from DB
    product_rows = query(
        "SELECT p.brand, p.model, p.category, p.price_aed, p.sku FROM products p WHERE p.brand=? AND p.model=? LIMIT 1",
        [brand, model]
    )
    product = product_rows[0] if product_rows else {}

    # Try to find a matching supplier by brand name
    supplier_rows = query(
        "SELECT s.name FROM suppliers s WHERE INSTR(LOWER(s.name), LOWER(?)) > 0 LIMIT 1",
        [brand]
    )
    supplier_name = supplier_rows[0]["name"] if supplier_rows else f"{brand} EMEA"

    prompt = f"""You are the procurement team at Advanced Media Trading LLC (AMT), Dubai — MENA's largest professional AV distributor.

Write a concise, professional reorder request email to the supplier. Use the live database data below.

Database records:
- Brand: {brand}
- Model: {model}
- SKU: {product.get('sku', 'N/A')}
- Category: {product.get('category', 'N/A')}
- Unit price: AED {product.get('price_aed', 'N/A')}
- Current available stock: {qty_available} unit(s)
- Reorder threshold: {reorder_point} unit(s)
- Matched supplier: {supplier_name}

Format as a plain-text email. Start with "Subject: ..." on the first line, then a blank line, then the body. Sign off as "AMT Procurement Team | procurement@amt.tv | +971 4 447 6000". No markdown, no asterisks."""

    try:
        client = _OAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=420
        )
        return jsonify({"email": resp.choices[0].message.content.strip(), "ok": True})
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/api/insights-data")
@login_required
def insights_data():
    return jsonify({
        "stock_by_category":   query("SELECT p.category, SUM(i.qty_on_hand-i.qty_reserved) AS qty FROM products p JOIN inventory i ON i.product_id=p.id GROUP BY p.category ORDER BY qty DESC"),
        "invoice_status":      query("SELECT status, COUNT(*) AS n, COALESCE(SUM(amount_aed),0) AS total FROM invoices GROUP BY status"),
        "order_status":        query("SELECT status, COUNT(*) AS n FROM orders GROUP BY status"),
        "revenue_by_month":    query("SELECT strftime('%Y-%m',order_date) AS month, ROUND(SUM(total_aed),0) AS total FROM orders WHERE status IN ('confirmed','shipped','delivered') GROUP BY month ORDER BY month"),
        "low_stock":           query("SELECT p.brand, p.model, SUM(i.qty_on_hand-i.qty_reserved) AS qty_available, MAX(i.reorder_point) AS reorder_point FROM products p JOIN inventory i ON i.product_id=p.id GROUP BY p.id HAVING qty_available <= reorder_point ORDER BY qty_available"),
        "ticket_status":       query("SELECT status, COUNT(*) AS n FROM service_tickets GROUP BY status"),
        "top_brands":          query("SELECT p.brand, COUNT(*) AS orders FROM order_items oi JOIN products p ON p.id=oi.product_id GROUP BY p.brand ORDER BY orders DESC LIMIT 8"),
        "shipment_status":     query("SELECT status, COUNT(*) AS n FROM shipments GROUP BY status"),
        "orders_by_country":   query("SELECT c.country, COUNT(*) AS n FROM orders o JOIN customers c ON c.id=o.customer_id GROUP BY c.country ORDER BY n DESC"),
    })


@app.route("/api/schema")
@login_required
def db_schema():
    _SKIP = {"sqlite_sequence", "chat_log"}
    con = sqlite3.connect(_DB)
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    schema = {}
    for t in tables:
        if t in _SKIP:
            continue
        cols = [{"name": r[1], "type": r[2], "pk": bool(r[5])}
                for r in con.execute(f"PRAGMA table_info({t})").fetchall()]
        schema[t] = cols
    con.close()
    return jsonify(schema)


@app.route("/history")
@login_required
def history_page():
    return render_template("history.html")


@app.route("/api/history", methods=["GET", "DELETE"])
@login_required
def history_api():
    if request.method == "DELETE":
        con = sqlite3.connect(_DB)
        con.execute("DELETE FROM chat_log")
        con.commit(); con.close()
        return jsonify({"ok": True})
    limit = request.args.get("limit", 200, type=int)
    con = sqlite3.connect(_DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id,dept,user_msg,ai_response,tools_json,tokens_json,ts FROM chat_log ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    con.close()
    return jsonify([{
        "id": r["id"], "dept": r["dept"],
        "user_msg": r["user_msg"], "ai_response": r["ai_response"],
        "tools": _json.loads(r["tools_json"] or "[]"),
        "tokens": _json.loads(r["tokens_json"] or "{}"),
        "ts": r["ts"]
    } for r in rows])


_briefing_cache = {"text": None, "ts": 0.0}
_BRIEFING_TTL = 600  # 10 minutes

@app.route("/api/briefing")
@login_required
def briefing():
    from openai import OpenAI as _OAI
    import time as _t
    if _briefing_cache["text"] and (_t.time() - _briefing_cache["ts"]) < _BRIEFING_TTL:
        return jsonify({"briefing": _briefing_cache["text"]})
    s = get_stats()
    alerts = []
    if s["distribution"]["delayed"] > 0:
        alerts.append(f"{s['distribution']['delayed']} shipment(s) delayed/held at customs")
    if s["finance"]["overdue"] > 0:
        alerts.append(f"{s['finance']['overdue']} invoice(s) overdue — AED {s['finance']['outstanding_aed']:,.0f} outstanding")
    if s["service"]["open"] > 0:
        alerts.append(f"{s['service']['open']} open service ticket(s)")
    if s["distribution"]["low_stock"] > 0:
        alerts.append(f"{s['distribution']['low_stock']} SKU(s) below reorder point")
    if not alerts:
        text = "All systems clear today — no critical alerts across operations, finance, or service."
        _briefing_cache["text"] = text; _briefing_cache["ts"] = _t.time()
        return jsonify({"briefing": text})
    prompt = f"You are AMT's AI ops assistant. Write a single sharp 2-sentence morning briefing for the ops team. Be direct and action-oriented. Current alerts: {'; '.join(alerts)}. Lead with the most urgent item."
    try:
        c = _OAI(api_key=os.getenv("OPENAI_API_KEY"))
        r = c.chat.completions.create(model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}], max_tokens=120)
        text = r.choices[0].message.content.strip()
        _briefing_cache["text"] = text; _briefing_cache["ts"] = _t.time()
        return jsonify({"briefing": text})
    except Exception:
        return jsonify({"briefing": "; ".join(alerts)})


@app.route("/api/restart", methods=["POST"])
@login_required
def restart_server():
    import sys, os, threading
    def _restart():
        import time; time.sleep(0.6)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=_restart, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
@login_required
def reset():
    data = request.get_json()
    department = data.get("department")
    if department:
        session.pop(f"history_{department}", None)
    else:
        session.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
