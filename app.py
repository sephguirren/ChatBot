from flask import Flask, render_template, request, jsonify
import random, json, pickle, nltk, datetime, re

# Load trained model + vectorizer
model = pickle.load(open("chatbot_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# Load intents with UTF-8 (for emojis)
with open("intents.json", encoding="utf-8") as f:
    intents = json.load(f)

app = Flask(__name__)

# Simple memory (expandable later)
user_memory = {"name": None}


def chatbot_response(msg: str) -> str:
    # Normalize input
    msg = msg.lower().strip()

    # 🔹 Check if user introduces their name
    name_match = re.search(r"(?:my name is|i am|i'm|call me)\s+(\w+)", msg)
    if name_match:
        name = name_match.group(1).capitalize()
        user_memory["name"] = name
        return f"Nice to meet you, {name}! I'll remember your name."

    # 🔹 If user asks "who am i?"
    if user_memory["name"] and "who am i" in msg:
        return f"You're {user_memory['name']}! 👋"

    # 🔹 Predict intent
    X = vectorizer.transform([msg])
    tag = model.predict(X)[0]
    prob = model.predict_proba(X).max()

    # Debug info in console
    print(f"[DEBUG] User: {msg} | Predicted: {tag} | Confidence: {prob:.2f}")

    # 🔹 Fallback if confidence is too low
    if prob < 0.2:
        for intent in intents["intents"]:
            if intent["tag"] == "fallback":
                return random.choice(intent["responses"])

    # 🔹 Special intents (dynamic answers)
    if tag == "time":
        return f"The current time is {datetime.datetime.now().strftime('%H:%M:%S')} ⏰"
    if tag == "date":
        return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')} 📅"

    # 🔹 Normal responses
    for intent in intents["intents"]:
        if intent["tag"] == tag:
            reply = random.choice(intent["responses"])
            # Insert memory if {name} is in response
            if "{name}" in reply and user_memory["name"]:
                reply = reply.replace("{name}", user_memory["name"])
            return reply

    return "Hmm, I’m not sure about that."


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/get", methods=["POST"])
def get_bot_response():
    user_msg = request.json.get("message")
    bot_reply = chatbot_response(user_msg)
    return jsonify({"reply": bot_reply})


if __name__ == "__main__":
    app.run(debug=True)
