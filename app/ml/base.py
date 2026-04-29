"""
🧠 ML Model Base System — StudyMind AI
────────────────────────────────────────────────────────────────────
- Safe stub behaviour (no crashes in production)
- Consistent predict() interface
- Ready for sklearn / torch integration
────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
import os
import pickle
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("studymind.ml")


# ─────────────────────────────────────────────
# BASE CLASS
# ─────────────────────────────────────────────
class BaseMLModel(ABC):
    model_path: str = ""

    @abstractmethod
    def train(self, X, y=None) -> "BaseMLModel":
        """Train model (override in subclass)."""

    @abstractmethod
    def predict(self, features: Any) -> Any:
        """Return prediction for given features (override in subclass)."""

    # ── Persistence ──────────────────────────────────────────────────────────
    def save(self, path: str | None = None) -> None:
        target = path or self.model_path
        if not target:
            raise ValueError("model_path is not set — pass an explicit path to save()")

        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)

        with open(target, "wb") as f:
            pickle.dump(self._get_artifact(), f)

        logger.info("Model saved → %s", target)

    def _get_artifact(self) -> Any:
        """
        Return the internal artifact to persist.
        Override to return only the inner model (e.g. self._model)
        rather than the whole wrapper instance.
        """
        return self

    @classmethod
    def load(cls, path: str) -> Any | None:
        if not os.path.exists(path):
            logger.warning("Model file not found at %s — using stub fallback", path)
            return None

        with open(path, "rb") as f:
            artifact = pickle.load(f)  # noqa: S301 — trusted internal path

        logger.info("Model loaded ← %s", path)
        return artifact


# ─────────────────────────────────────────────
# 1. STUDY OPTIMIZER
# ─────────────────────────────────────────────
class StudyOptimizer(BaseMLModel):
    """Predict optimal study hours based on past behaviour."""

    model_path = "ml_models/study_optimizer.pkl"

    def __init__(self) -> None:
        self._model = None

    def train(self, X, y) -> "StudyOptimizer":
        # Swap in a real sklearn estimator here when ready
        self._model = None
        return self

    def _get_artifact(self) -> Any:
        return self._model

    def predict(self, features: dict) -> dict:
        if self._model is not None:
            return self._model.predict([features])

        # Stub: echo back the hour from features
        hour = int(features.get("hour", 20))
        return {
            "optimal_hours": [hour, hour + 1, hour + 2],
            "productivity": 0.7,
        }


# ─────────────────────────────────────────────
# 2. TASK DIFFICULTY PREDICTOR
# ─────────────────────────────────────────────
_HARD_KEYWORDS   = frozenset({"exam", "final", "project", "dissertation", "thesis"})
_MEDIUM_KEYWORDS = frozenset({"quiz", "review", "assignment", "homework"})


class DifficultyPredictor(BaseMLModel):
    """Score task difficulty on a 0–1 scale."""

    model_path = "ml_models/difficulty.pkl"

    def __init__(self) -> None:
        self._classifier = None

    def train(self, tasks: list[dict], labels: list[float]) -> "DifficultyPredictor":
        self._classifier = None
        return self

    def _get_artifact(self) -> Any:
        return self._classifier

    def predict(self, task: dict) -> dict:
        if self._classifier is not None:
            text = task.get("title", "") + " " + " ".join(task.get("tags", []))
            return self._classifier.predict([text])

        lower = (task.get("title", "") + " " + " ".join(task.get("tags", []))).lower()

        if _HARD_KEYWORDS & set(lower.split()):
            label, score = "hard", 0.8
        elif _MEDIUM_KEYWORDS & set(lower.split()):
            label, score = "medium", 0.5
        else:
            label, score = "easy", 0.2

        return {
            "label": label,
            "score": score,
            "suggested_minutes": task.get("estimated_minutes", 60),
        }


# ─────────────────────────────────────────────
# 3. RETENTION MODEL  (SM-2 + ML ready)
# ─────────────────────────────────────────────
class RetentionModel(BaseMLModel):
    """Estimate flashcard retention probability using the SM-2 algorithm."""

    model_path = "ml_models/retention.pkl"

    def __init__(self) -> None:
        self._model = None

    def train(self, review_logs: list[dict]) -> "RetentionModel":
        self._model = None
        return self

    def _get_artifact(self) -> Any:
        return self._model

    def predict(self, card: dict) -> dict:
        if self._model is not None:
            return self._model.predict(card)

        ease_factor = card.get("ease_factor", 2.5)
        interval    = card.get("interval", 1)
        reps        = card.get("repetitions", 0)

        stability  = ease_factor * max(reps, 1)
        retention  = max(0.1, min(0.95, 1.0 - interval / (stability * 2)))

        return {
            "retention_probability": round(retention, 3),
            "should_review_now":     retention < 0.5,
        }


# ─────────────────────────────────────────────
# 4. TOPIC CLUSTERER
# ─────────────────────────────────────────────
class TopicClusterer(BaseMLModel):
    """Group notes into topic clusters (stub uses subject field)."""

    model_path = "ml_models/topic_cluster.pkl"

    def __init__(self, n_clusters: int = 8) -> None:
        self.n_clusters  = n_clusters
        self._clusterer  = None

    def train(self, notes: list[dict]) -> "TopicClusterer":
        self._clusterer = None
        return self

    def _get_artifact(self) -> Any:
        return self._clusterer

    def predict(self, notes: list[dict]) -> dict:
        if not notes:
            return {"clusters": {}, "mode": "stub"}

        if self._clusterer is not None:
            return self._clusterer.predict(notes)

        # Stub: bucket by subject
        clusters: dict[str, list] = {}
        for note in notes:
            key = note.get("subject") or "General"
            clusters.setdefault(key, []).append(note.get("id") or note.get("title"))

        return {"clusters": clusters, "mode": "stub"}
