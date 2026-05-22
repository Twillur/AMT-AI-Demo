import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "amt-demo-2026")

from agents import sales, distribution, finance, service

AGENTS = {
    "sales": sales,
    "distribution": distribution,
    "finance": finance,
    "service": service,
}

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
