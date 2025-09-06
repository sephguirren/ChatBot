from flask import Flask, request, jsonify, render_template
import json
import random
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer

app = Flask(__name__)

# Load intents + model + vectorizer
with open("intents.json", encoding="utf-8") as f:
    intents = json.load(f)

model = pickle.load(open("chatbot_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

def chatbot_response(user_msg):
    X = vectorizer.transform([user_msg])
    intent = model.predict(X)[0]

    for intent_obj in intents["intents"]:
        if intent_obj["tag"] == intent:
            return random.choice(intent_obj["responses"])

    return "Sorry, I didn’t quite get that 🤔"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get", methods=["POST"])
def get_bot_response():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        reply = chatbot_response(user_msg)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
