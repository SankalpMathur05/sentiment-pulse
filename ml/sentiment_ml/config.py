"""Central settings for the ML pipeline: random seeds, labels and file locations.

Everything that affects reproducibility lives here so it is set in exactly one place.
"""
from __future__ import annotations

import os
from pathlib import Path

# One seed for every random operation (split, cross-validation shuffles, model solvers).
RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5

# Fixed label order used for metrics, probabilities and the confusion matrix.
LABELS: tuple[str, ...] = ("negative", "neutral", "positive")

MODEL_NAME = "tfidf-logreg"
MODEL_SEMVER = "1.0.0"

# The repo root can be overridden when the package is installed outside the repo.
REPO_ROOT = Path(os.environ.get("SENTIMENT_REPO_ROOT", Path(__file__).resolve().parents[2]))
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "models"
REPORTS_DIR = REPO_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
