"""Load a saved model artifact and make predictions. This is what the API uses.

The API only needs this module (plus preprocessing/explain); it never retrains.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np

from .artifacts import sha256_file
from .explain import word_contributions


@dataclass(frozen=True)
class Prediction:
    sentiment: str
    confidence: float
    probabilities: dict[str, float]
    top_words: list[dict] = field(default_factory=list)


class SentimentModel:
    """A fitted pipeline (cleaner -> TF-IDF -> Logistic Regression) plus its metadata."""

    def __init__(self, pipeline, metadata: dict) -> None:
        self.pipeline = pipeline
        self.metadata = metadata
        self.version: str = metadata["version"]
        self._cleaner = pipeline.named_steps["clean"]
        self._vectorizer = pipeline.named_steps["tfidf"]
        self._clf = pipeline.named_steps["clf"]
        self.labels: list[str] = [str(label) for label in self._clf.classes_]
        self._feature_names = self._vectorizer.get_feature_names_out()

    @classmethod
    def load(cls, model_dir: str | Path) -> "SentimentModel":
        model_dir = Path(model_dir)
        metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
        model_path = model_dir / "model.joblib"
        if sha256_file(model_path) != metadata["artifact_sha256"]:
            raise ValueError(f"{model_path} does not match the checksum in metadata.json")
        return cls(joblib.load(model_path), metadata)

    def normalize(self, text: str) -> str:
        """The exact text the model sees. Two posts with the same normalised text always
        get the same prediction, which is what makes it a safe cache key."""
        return self._cleaner.transform([text])[0]

    def predict(self, text: str, top_k: int = 5) -> Prediction:
        return self.predict_many([text], top_k=top_k)[0]

    def predict_many(self, texts: list[str], top_k: int = 5) -> list[Prediction]:
        cleaned = self._cleaner.transform(texts)
        features = self._vectorizer.transform(cleaned)
        probabilities = self._clf.predict_proba(features)
        predictions = []
        for row_index, proba in enumerate(probabilities):
            best = int(np.argmax(proba))
            predictions.append(Prediction(
                sentiment=self.labels[best],
                confidence=round(float(proba[best]), 4),
                probabilities={label: round(float(p), 4) for label, p in zip(self.labels, proba)},
                top_words=word_contributions(self._clf, self._feature_names, features[row_index], best, top_k),
            ))
        return predictions
