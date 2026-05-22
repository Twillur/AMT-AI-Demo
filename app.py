import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "amt-demo-2026")

from agents import sales, distribution, finance, service
from agents.db_utils import query

AGENTS = {
    "sales": sales,
    "distribution": distribution,
    "finance": finance,
    "service": service,
}

def get_stats():
    sales_stats = {
        "products": query("SELECT COUNT(*) AS n FROM products")[0]["n"],
        "orders_active": query("SELECT COUNT(*) AS n FROM orders WHERE status IN ('confirmed','shipped')")[0]["n"],
        "top_brand": query("SELECT brand, COUNT(*) AS n FROM products GROUP BY brand ORDER BY n DESC LIMIT 1")[0]["brand"],
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
    }
    svc_stats = {
        "open": query("SELECT COUNT(*) AS n FROM service_tickets WHERE status='open'")[0]["n"],
        "in_repair": query("SELECT COUNT(*) AS n FROM service_tickets WHERE status IN ('in_repair','diagnosed','awaiting_parts')")[0]["n"],
        "ready": query("SELECT COUNT(*) AS n FROM service_tickets WHERE status='ready'")[0]["n"],
    }
    return {"sales": sales_stats, "distribution": dist_stats, "finance": fin_stats, "service": svc_stats}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    department = data.get("department", "sales")
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "No message provided"}), 400

    agent = AGENTS.get(department)
    if not agent:
        return jsonify({"error": "Unknown department"}), 400

    history_key = f"history_{department}"
    history = session.get(history_key, [])

    try:
        response_text = agent.run(message, history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response_text})
    if len(history) > 20:
        history = history[-20:]
    session[history_key] = history

    return jsonify({"response": response_text})

@app.route("/api/stats")
def stats():
    return jsonify(get_stats())

@app.route("/api/reset", methods=["POST"])
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
