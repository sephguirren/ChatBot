import os
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import random
import json
import pickle
import mysql.connector
from datetime import datetime

# -------------------------
# Configuration
# -------------------------
app = Flask(__name__)

# Use environment secret if available, otherwise fallback (change before sharing)
app.secret_key = os.environ.get("CHATBOT_SECRET_KEY", "please_change_this_secret")

# Admin credentials from environment (safer). Defaults are for local dev only.
ADMIN_USERNAME = os.environ.get("CHATBOT_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("CHATBOT_ADMIN_PASS", "password123")

# -------------------------
# Load model & intents
# -------------------------
with open("intents.json", encoding="utf-8") as f:
    intents = json.load(f)

# load model & vectorizer if present (optional)
model = None
vectorizer = None
if os.path.exists("chatbot_model.pkl") and os.path.exists("vectorizer.pkl"):
    with open("chatbot_model.pkl", "rb") as mf:
        model = pickle.load(mf)
    with open("vectorizer.pkl", "rb") as vf:
        vectorizer = pickle.load(vf)
    print("[INFO] Model and vectorizer loaded", flush=True)
else:
    print("[WARNING] No model/vectorizer found; running in keyword mode", flush=True)

# -------------------------
# DB (MySQL) connection
# -------------------------
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("CHATBOT_DB_HOST", "localhost"),
        user=os.environ.get("CHATBOT_DB_USER", "root"),
        password=os.environ.get("CHATBOT_DB_PASS", ""),
        database=os.environ.get("CHATBOT_DB_NAME", "chatbot_db")
    )

# Create tables if not exist (safe on each run)
def ensure_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_message TEXT,
        bot_response TEXT,
        timestamp DATETIME
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS knowledge (
        id INT AUTO_INCREMENT PRIMARY KEY,
        question TEXT UNIQUE,
        answer TEXT
    )
    """)
    conn.commit()
    cur.close()
    conn.close()

ensure_tables()

# -------------------------
# Auth decorator
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# -------------------------
# Helper DB functions
# -------------------------
def log_chat(user_msg, bot_resp):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO chat_logs (user_message, bot_response, timestamp) VALUES (%s, %s, %s)",
                (user_msg, bot_resp, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

def search_knowledge_exact(user_msg):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT answer FROM knowledge WHERE question = %s", (user_msg,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None

def save_knowledge(question, answer):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO knowledge (question, answer) VALUES (%s, %s)", (question, answer))
    conn.commit()
    cur.close()
    conn.close()

def fetch_recent_chats(limit=50):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, user_message, bot_response, timestamp FROM chat_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_knowledge():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, question, answer FROM knowledge ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def delete_knowledge_entry(k_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM knowledge WHERE id=%s", (k_id,))
    conn.commit()
    cur.close()
    conn.close()

# -------------------------
# Chat logic
# -------------------------
def extract_name(text):
    import re
    patterns = [r"my name is (\w+)", r"i am (\w+)", r"i'm (\w+)", r"call me (\w+)"]
    for p in patterns:
        m = re.search(p, text.lower())
        if m:
            return m.group(1).capitalize()
    return None

def chatbot_response(user_msg):
    # 1) check DB knowledge (exact)
    learned = search_knowledge_exact(user_msg)
    if learned:
        log_chat(user_msg, learned)
        return learned

    # 2) teach mode
    if user_msg.lower().strip().startswith("teach:"):
        try:
            content = user_msg[6:].strip()
            question, answer = content.split("=", 1)
            save_knowledge(question.strip(), answer.strip())
            resp = f"✅ Got it! I’ve learned how to answer: '{question.strip()}'"
            log_chat(user_msg, resp)
            return resp
        except Exception as e:
            resp = "⚠️ Teaching failed. Use: teach: question=answer"
            log_chat(user_msg, resp)
            return resp

    # 3) ML model if present
    if model and vectorizer:
        try:
            X = vectorizer.transform([user_msg])
            tag = model.predict(X)[0]
            for intent_obj in intents["intents"]:
                if intent_obj["tag"] == tag:
                    reply = random.choice(intent_obj["responses"])
                    log_chat(user_msg, reply)
                    return reply
        except Exception as e:
            print("[MODEL ERROR]", e, flush=True)

    # 4) fallback keyword handling
    u = user_msg.lower()
    if "hi" in u or "hello" in u:
        resp = "Hello! 👋 How can I help you today?"
        log_chat(user_msg, resp)
        return resp
    if "who are you" in u or "your name" in u:
        resp = "I'm your virtual assistant bot 🤖"
        log_chat(user_msg, resp)
        return resp
    if "time" in u:
        from datetime import datetime
        resp = "⏰ Current time: " + datetime.now().strftime("%H:%M:%S")
        log_chat(user_msg, resp)
        return resp

    resp = random.choice(["Sorry, I didn’t quite get that 🤔", "Can you rephrase your question?"])
    log_chat(user_msg, resp)
    return resp

# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get", methods=["POST"])
def get_bot_response():
    data = request.get_json() or {}
    user_msg = data.get("message", "")
    reply = chatbot_response(user_msg)
    return jsonify({"reply": reply})

# Login routes
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

# Admin dashboard - protected
@app.route("/admin")
@login_required
def admin():
    logs = fetch_recent_chats(50)
    knowledge = fetch_knowledge()
    return render_template("admin.html", logs=logs, knowledge=knowledge)

@app.route("/delete_knowledge/<int:k_id>", methods=["POST"])
@login_required
def delete_knowledge(k_id):
    delete_knowledge_entry(k_id)
    return redirect(url_for("admin"))

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    # For local dev use; in production use gunicorn etc.
    app.run(debug=True)
