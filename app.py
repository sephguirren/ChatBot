from flask import Flask, request, jsonify, render_template
import json
import random
import os
import pickle
from datetime import datetime
import re
import mysql.connector

app = Flask(__name__)

# --- Load intents.json ---
with open("intents.json", encoding="utf-8") as f:
    intents = json.load(f)

# --- Load ML model if available ---
model, vectorizer = None, None
if os.path.exists("chatbot_model.pkl") and os.path.exists("vectorizer.pkl"):
    with open("chatbot_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open("vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    print("[INFO] Model and vectorizer loaded successfully", flush=True)
else:
    print("[WARNING] Model/vectorizer not found. Running in keyword mode.", flush=True)


# ===============================
# 📌 DATABASE CONNECTION
# ===============================
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # default XAMPP user
        password="",          # leave empty unless you set one
        database="chatbot_db" # the DB you created
    )


def log_conversation(user_msg, bot_reply):
    """Save user and bot messages to DB"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (user_message, bot_reply) VALUES (%s, %s)",
        (user_msg, bot_reply)
    )
    conn.commit()
    conn.close()


def save_knowledge(question, answer):
    """Save new learned Q&A into DB"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO knowledge (question, answer) VALUES (%s, %s)",
        (question, answer)
    )
    conn.commit()
    conn.close()


def search_knowledge(user_msg):
    """Search knowledge base for exact match"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM knowledge WHERE question = %s", (user_msg,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


# ===============================
# 📌 CHATBOT LOGIC
# ===============================
def chatbot_response(user_msg):
    user_msg_lower = user_msg.lower()

    # --- check learned knowledge first ---
    learned = search_knowledge(user_msg)
    if learned:
        return learned

    # --- allow teaching new Q&A ---
    if user_msg_lower.startswith("teach:"):
        try:
            # format: teach: What is AI?=AI means Artificial Intelligence.
            content = user_msg[6:].strip()
            question, answer = content.split("=", 1)
            save_knowledge(question.strip(), answer.strip())
            return f"✅ Got it! I’ve learned how to answer: '{question.strip()}'"
        except:
            return "⚠️ Oops! Use this format: teach: question=answer"

    # --- if ML model exists, try predicting intent ---
    if model and vectorizer:
        try:
            X = vectorizer.transform([user_msg])
            intent = model.predict(X)[0]

            # special handling
            if intent == "time":
                return f"⏰ Current time: {datetime.now().strftime('%H:%M:%S')}"
            if intent == "date":
                return f"📅 Today is {datetime.now().strftime('%A, %B %d, %Y')}"
            if intent == "ask_name":
                name = extract_name(user_msg)
                if name:
                    return f"Nice to meet you, {name}! 😊"
                return "I’d love to know your name!"

            for intent_obj in intents["intents"]:
                if intent_obj["tag"] == intent:
                    return random.choice(intent_obj["responses"])
        except Exception as e:
            print("[ERROR in model prediction]", str(e), flush=True)

    # --- fallback keyword rules ---
    if "time" in user_msg_lower:
        return f"⏰ Current time: {datetime.now().strftime('%H:%M:%S')}"
    if "date" in user_msg_lower or "day" in user_msg_lower:
        return f"📅 Today is {datetime.now().strftime('%A, %B %d, %Y')}"
    if "who are you" in user_msg_lower or "your name" in user_msg_lower:
        return "I'm your virtual assistant bot 🤖"
    if "bye" in user_msg_lower or "goodbye" in user_msg_lower:
        return "Goodbye! 👋 Have a nice day!"

    # --- final fallback ---
    return random.choice([
        "Sorry, I didn’t quite get that 🤔",
        "Can you rephrase your question?"
    ])


# ===============================
# 📌 HELPERS
# ===============================
def extract_name(text):
    patterns = [
        r"my name is (\w+)",
        r"i am (\w+)",
        r"i'm (\w+)",
        r"call me (\w+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1).capitalize()
    return None


# ===============================
# 📌 ROUTES
# ===============================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/get", methods=["POST"])
def get_bot_response():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        reply = chatbot_response(user_msg)

        # log conversation to MySQL
        log_conversation(user_msg, reply)

        return jsonify({"reply": reply})
    except Exception as e:
        print("[FATAL ERROR]", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
