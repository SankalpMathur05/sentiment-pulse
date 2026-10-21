"""Held-out test evaluation: metrics, confusion matrix and confidence calibration.

This runs ONCE, after every modelling decision has been made with cross-validation.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)

from . import config
from .reporting import save_figure


def classification_metrics(y_true, y_pred, proba: np.ndarray | None = None, proba_labels=None) -> dict:
    labels = list(config.LABELS)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro",
                                                                    zero_division=0)
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(macro_p),
        "macro_recall": float(macro_r),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)),
        "per_class": {lbl: {"precision": float(report[lbl]["precision"]), "recall": float(report[lbl]["recall"]),
                            "f1": float(report[lbl]["f1-score"]), "support": int(report[lbl]["support"])}
                      for lbl in labels},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "confusion_labels": labels,
    }
    if proba is not None:
        order = [list(proba_labels).index(lbl) for lbl in labels]
        proba = proba[:, order]
        one_hot = (np.asarray(y_true)[:, None] == np.array(labels)[None, :]).astype(float)
        metrics["log_loss"] = float(log_loss(y_true, proba, labels=labels))
        # Multi-class Brier score: mean squared distance between probabilities and the truth (0 = perfect).
        metrics["brier_score"] = float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))
    return metrics


def plot_confusion_matrix(matrix: list[list[int]], title: str, name: str) -> str:
    counts = np.array(matrix)
    row_pct = counts / counts.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    ax.imshow(row_pct, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(config.LABELS)), labels=config.LABELS)
    ax.set_yticks(range(len(config.LABELS)), labels=config.LABELS)
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title(title)
    for i in range(counts.shape[0]):
        for j in range(counts.shape[1]):
            colour = "white" if row_pct[i, j] > 0.5 else "black"
            ax.text(j, i, f"{counts[i, j]}\n{row_pct[i, j]:.0%}", ha="center", va="center", color=colour, fontsize=9)
    return save_figure(fig, name)


def calibration_table(y_true, y_pred, confidence: np.ndarray, bins=(0.33, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001)) -> list[dict]:
    """For each confidence band: how many predictions fall in it and how often they are right."""
    frame = pd.DataFrame({"correct": np.asarray(y_true) == np.asarray(y_pred), "confidence": confidence})
    frame["band"] = pd.cut(frame["confidence"], bins=bins, right=False)
    rows = []
    for band, group in frame.groupby("band", observed=True):
        rows.append({"band": f"{band.left:.2f}–{min(band.right, 1.0):.2f}", "count": int(len(group)),
                     "share": float(len(group) / len(frame)), "mean_confidence": float(group["confidence"].mean()),
                     "accuracy": float(group["correct"].mean())})
    return rows


def plot_calibration(rows: list[dict], name: str) -> str:
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    ax.plot([0.3, 1], [0.3, 1], linestyle="--", color="#94a3b8", label="perfectly calibrated")
    ax.plot([r["mean_confidence"] for r in rows], [r["accuracy"] for r in rows], marker="o", color="#6366f1",
            label="model")
    ax.set_xlabel("Average predicted confidence")
    ax.set_ylabel("Actual accuracy")
    ax.set_title("Is the confidence score honest?")
    ax.legend(loc="upper left")
    return save_figure(fig, name)


def accuracy_by_label_agreement(test: pd.DataFrame, y_pred) -> list[dict]:
    """Model accuracy on tweets where annotators agreed vs. disagreed."""
    frame = test.assign(correct=np.asarray(y_pred) == test["label"].to_numpy())
    bands = {"confidence = 1.0 (annotators fully agreed)": frame["label_confidence"] >= 0.999,
             "0.7 ≤ confidence < 1.0": (frame["label_confidence"] >= 0.7) & (frame["label_confidence"] < 0.999),
             "confidence < 0.7 (noisy label)": frame["label_confidence"] < 0.7}
    return [{"band": name, "count": int(mask.sum()), "accuracy": float(frame.loc[mask, "correct"].mean())}
            for name, mask in bands.items() if mask.any()]
