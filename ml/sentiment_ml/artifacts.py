"""Saving and fingerprinting model artifacts.

A model artifact is a folder containing:
  model.joblib   the fitted scikit-learn pipeline (cleaner -> TF-IDF -> classifier)
  metadata.json  version, checksum, training settings, dataset info and metrics

The version string includes the first 8 characters of the model file's SHA-256, so
even if someone retrains without bumping the semantic version, the version (and
therefore every Redis cache key) changes and stale predictions are never reused.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib

from .preprocessing import PREPROCESSING_VERSION


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_version(name: str, semver: str, sha256: str) -> str:
    return f"{name}@{semver}+{sha256[:8]}"


def save_model(pipeline, metadata: dict, out_dir: Path) -> dict:
    """Write model.joblib + metadata.json and return the completed metadata."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "model.joblib"
    joblib.dump(pipeline, model_path, compress=3)
    sha = sha256_file(model_path)
    metadata = {
        "preprocessing_version": PREPROCESSING_VERSION,
        **metadata,
        "artifact_sha256": sha,
        "version": build_version(metadata["name"], metadata["semver"], sha),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
    return metadata
