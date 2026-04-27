# train_models.py
import os
import pickle
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

os.makedirs("app/ml_models", exist_ok=True)

print("🚀 Training ML Models for MonkeyMind AI")

# 1. Difficulty Predictor
print("📚 Training difficulty predictor...")
texts = ["exam", "quiz", "homework", "project", "reading", "review"]
labels = ["hard", "medium", "easy", "hard", "easy", "medium"]
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(texts)
model = LogisticRegression()
model.fit(X, labels)
with open("app/ml_models/difficulty.pkl", "wb") as f:
    pickle.dump(model, f)

# 2. Retention Model
print("🧠 Training retention model...")
X_ret = np.random.rand(500, 5)
y_ret = np.random.randint(0, 2, 500)
retention = GradientBoostingClassifier()
retention.fit(X_ret, y_ret)
with open("app/ml_models/retention.pkl", "wb") as f:
    pickle.dump(retention, f)

# 3. Study Optimizer
print("⏰ Training study optimizer...")
X_study = np.random.rand(1000, 4)
y_productivity = np.random.rand(1000)
optimizer = RandomForestRegressor()
optimizer.fit(X_study, y_productivity)
with open("app/ml_models/study_optimizer.pkl", "wb") as f:
    pickle.dump(optimizer, f)

print("✅ All models trained!")
