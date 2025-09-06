import json
import pickle
import random
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# Download tokenizer
nltk.download("punkt")

# Load intents
with open("intents.json", encoding="utf-8") as f:
    data = json.load(f)

corpus = []
tags = []

for intent in data["intents"]:
    for pattern in intent["patterns"]:
        corpus.append(pattern.lower())  # lowercase input
        tags.append(intent["tag"])

# Vectorize
vectorizer = TfidfVectorizer(tokenizer=nltk.word_tokenize)
X = vectorizer.fit_transform(corpus)

# Train Naive Bayes
model = MultinomialNB()
model.fit(X, tags)

# Save model + vectorizer
with open("chatbot_model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("vectorizer.pkl", "wb") as f:
    pickle.dump(vectorizer, f)

print("✅ Training complete. Model saved!")
