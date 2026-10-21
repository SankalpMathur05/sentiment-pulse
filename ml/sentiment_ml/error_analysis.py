"""Find and tag the model's mistakes on the test set.

Tags are simple heuristics that SUGGEST why a post was misclassified. They are a
starting point for reading the examples by hand, not a second model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_NEGATIONS = {"not", "no", "never", "nothing", "nobody", "none", "cannot", "without"}


def _strong_words(clf, feature_names, label: str, k: int = 60) -> set[str]:
    index = list(clf.classes_).index(label)
    return {str(feature_names[i]) for i in np.argsort(-clf.coef_[index])[:k] if " " not in str(feature_names[i])}


def tag_errors(errors: pd.DataFrame, clf, feature_names) -> pd.DataFrame:
    positive_words = _strong_words(clf, feature_names, "positive")
    negative_words = _strong_words(clf, feature_names, "negative")

    def tags_for(row) -> list[str]:
        tokens = set(row.clean_text.split())
        tags = []
        if row.label_confidence < 0.7:
            tags.append("label noise (annotators disagreed)")
        if tokens & _NEGATIONS or any(t.endswith("n't") for t in tokens):
            tags.append("negation")
        if tokens & positive_words and tokens & negative_words:
            tags.append("mixed sentiment")
        if row.label == "negative" and row.predicted == "positive" and tokens & positive_words:
            tags.append("possible sarcasm / polite complaint")
        if "?" in tokens and "neutral" in (row.label, row.predicted):
            tags.append("question vs. opinion")
        if len(tokens) <= 5:
            tags.append("very short / little context")
        return tags or ["no obvious pattern"]

    errors = errors.copy()
    errors["tags"] = [tags_for(row) for row in errors.itertuples()]
    return errors


def misclassified(test: pd.DataFrame, y_pred, proba: np.ndarray, clf, feature_names) -> pd.DataFrame:
    frame = test.assign(predicted=y_pred, confidence=proba.max(axis=1))
    errors = frame[frame["label"] != frame["predicted"]]
    return tag_errors(errors, clf, feature_names)


def sample_errors(errors: pd.DataFrame, per_pair: int = 4) -> pd.DataFrame:
    """The most confident mistakes for each (true -> predicted) pair: the most informative ones."""
    return (errors.sort_values("confidence", ascending=False)
            .groupby(["label", "predicted"], sort=True)
            .head(per_pair)
            .sort_values(["label", "predicted", "confidence"], ascending=[True, True, False]))


def tag_counts(errors: pd.DataFrame) -> list[list]:
    counts = errors["tags"].explode().value_counts()
    return [[tag, int(n), f"{n / len(errors):.0%}"] for tag, n in counts.items()]


def pair_counts(errors: pd.DataFrame) -> list[list]:
    counts = errors.groupby(["label", "predicted"]).size().sort_values(ascending=False)
    return [[f"{true} → {pred}", int(n)] for (true, pred), n in counts.items()]
