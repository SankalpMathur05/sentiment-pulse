"""Explain predictions of a linear model in terms of the words in the post.

For Logistic Regression, the score for a class is a sum over words:
    score(class) = bias(class) + sum_over_words( tfidf_value(word) * weight(class, word) )
so each word's *contribution* to the predicted class is simply tfidf_value * weight.
The words with the largest positive contributions are the ones that pushed the
model towards its answer. This is exact for the model (no approximation), but it
explains the MODEL's reasoning, not the "true" sentiment of the post.
"""
from __future__ import annotations

import emoji
import numpy as np

_PLACEHOLDER_DISPLAY = {
    "<user>": "@mention",
    "<url>": "link",
    "<smile>": ":)",
    "<sad>": ":(",
    "<laugh>": ":D",
    "<wink>": ";)",
    "<tongue>": ":P",
    "<skeptical>": ":/",
    "<heart>": "<3",
    "<brokenheart>": "</3",
}
# Lower-cased emoji names (as produced by the cleaner) -> the emoji character.
_EMOJI_BY_NAME = {data["en"].lower(): char for char, data in emoji.EMOJI_DATA.items()}


def display_token(token: str) -> str:
    """Human-friendly form of a model token (handles bigrams, emojis and placeholders)."""
    parts = []
    for part in token.split(" "):
        if part in _PLACEHOLDER_DISPLAY:
            parts.append(_PLACEHOLDER_DISPLAY[part])
        elif part.startswith(":") and part.endswith(":") and len(part) > 2:
            parts.append(_EMOJI_BY_NAME.get(part, part))
        else:
            parts.append(part)
    return " ".join(parts)


def word_contributions(clf, feature_names: np.ndarray, features, class_index: int, top_k: int = 5) -> list[dict]:
    """Top words in ONE post that pushed the model towards `class_index`."""
    row = features.tocsr()
    if row.nnz == 0:
        return []
    weights = clf.coef_[class_index][row.indices]
    contributions = row.data * weights
    order = np.argsort(-contributions)
    result = []
    for i in order[:top_k]:
        if contributions[i] <= 0:
            break
        token = str(feature_names[row.indices[i]])
        result.append({"token": token, "display": display_token(token), "weight": round(float(contributions[i]), 4)})
    return result


def top_features_per_class(clf, feature_names: np.ndarray, top_k: int = 15) -> dict[str, list[dict]]:
    """The words the model most strongly associates with each class overall."""
    result = {}
    for class_index, label in enumerate(clf.classes_):
        order = np.argsort(-clf.coef_[class_index])[:top_k]
        result[str(label)] = [
            {"token": str(feature_names[i]), "display": display_token(str(feature_names[i])),
             "weight": round(float(clf.coef_[class_index][i]), 4)}
            for i in order
        ]
    return result
