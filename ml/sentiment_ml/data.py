"""Download, validate, de-duplicate and split the datasets.

Order of operations matters for honesty:
  1. validate + drop invalid rows
  2. de-duplicate (on the *cleaned* text, so near-identical tweets cannot end up in
     both train and test: that would be leakage)
  3. stratified train/test split
  4. only then fit anything (the vectoriser is fitted inside the training pipeline)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
from sklearn.model_selection import train_test_split

from . import config
from .artifacts import sha256_file
from .preprocessing import clean_text


@dataclass(frozen=True)
class DatasetSource:
    name: str
    url: str
    path: Path
    sha256: str | None
    licence: str
    homepage: str


AIRLINE = DatasetSource(
    name="Twitter US Airline Sentiment (CrowdFlower / Figure Eight)",
    url="https://huggingface.co/datasets/osanseviero/twitter-airline-sentiment/resolve/main/Tweets.csv",
    path=config.RAW_DIR / "Tweets.csv",
    # Pinned fingerprint: any changed or corrupted copy is rejected instead of silently used.
    sha256="ea94b23f41892b290dec3330bb8cf9cb6b8bc669eaae5f3a84c40f7b0de8f15e",
    licence="CC BY-NC-SA 4.0",
    homepage="https://www.kaggle.com/datasets/crowdflower/twitter-airline-sentiment",
)

_TWEETEVAL_BASE = "https://huggingface.co/datasets/cardiffnlp/tweet_eval/resolve/main/sentiment"
TWEETEVAL_SPLITS = {
    split: DatasetSource(
        name=f"TweetEval sentiment ({split})",
        url=f"{_TWEETEVAL_BASE}/{split}-00000-of-00001.parquet",
        path=config.EXTERNAL_DIR / "tweet_eval" / f"{split}.parquet",
        sha256=None,
        licence="CC BY 3.0 (plus Twitter Terms of Service)",
        homepage="https://huggingface.co/datasets/cardiffnlp/tweet_eval",
    )
    for split in ("train", "validation", "test")
}
TWEETEVAL_LABELS = {0: "negative", 1: "neutral", 2: "positive"}

AIRLINE_REQUIRED_COLUMNS = ["tweet_id", "airline_sentiment", "airline_sentiment_confidence", "airline", "text"]

# The published airline CSV contains find-and-replace damage: the dataset creators replaced
# every "late" and "cancel" (and some "book") substrings with complaint-category names,
# e.g. "chocolate" -> "chocoLate Flight", "rebook" -> "reFlight Booking Problems".
# The natural words "late" and "cancel" appear ZERO times, so without this repair the model
# could never learn the most common airline complaints. Real posts never contain these
# strings, so the repair lives here (dataset-specific), not in clean_text (which also runs
# on live API input).
AIRLINE_TEXT_ARTIFACTS = (
    ("Cancelled Flight", "cancel"),
    ("Late Flight", "late"),
    ("Flight Booking Problems", "book"),
)


def repair_airline_artifacts(text: str) -> str:
    for artifact, original in AIRLINE_TEXT_ARTIFACTS:
        text = text.replace(artifact, original)
    return text


def ensure_downloaded(source: DatasetSource) -> Path:
    """Download the file if it is missing, then verify its checksum when one is pinned."""
    if not source.path.exists():
        source.path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(source.url, timeout=120)
        response.raise_for_status()
        source.path.write_bytes(response.content)
    if source.sha256 and sha256_file(source.path) != source.sha256:
        raise ValueError(f"Checksum mismatch for {source.path}. Delete it and re-run to download again.")
    return source.path


def load_airline_raw() -> pd.DataFrame:
    df = pd.read_csv(ensure_downloaded(AIRLINE))
    missing = [c for c in AIRLINE_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {missing}")
    return df


def load_tweeteval() -> pd.DataFrame:
    """All TweetEval sentiment rows (train + validation + test) with string labels."""
    frames = []
    for split, source in TWEETEVAL_SPLITS.items():
        frame = pd.read_parquet(ensure_downloaded(source))
        frame["source_split"] = split
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    df["label"] = df["label"].map(TWEETEVAL_LABELS)
    return df


def prepare(df: pd.DataFrame, text_col: str, label_col: str) -> tuple[pd.DataFrame, dict]:
    """Validate, clean and de-duplicate. Returns the clean frame and a report of every count."""
    report: dict[str, int] = {"rows_raw": len(df)}
    df = df.rename(columns={text_col: "text", label_col: "label"}).copy()

    report["missing_text"] = int(df["text"].isna().sum())
    report["missing_label"] = int(df["label"].isna().sum())
    df = df.dropna(subset=["text", "label"])

    df["text"] = df["text"].astype(str).str.strip()
    empty = df["text"].eq("")
    report["empty_text"] = int(empty.sum())
    df = df[~empty]

    df["label"] = df["label"].astype(str).str.strip().str.lower()
    invalid = ~df["label"].isin(config.LABELS)
    report["invalid_label"] = int(invalid.sum())
    df = df[~invalid]

    if "tweet_id" in df.columns:
        dup_ids = df.duplicated(subset="tweet_id")
        report["duplicate_tweet_id"] = int(dup_ids.sum())
        df = df[~dup_ids]

    report["duplicate_raw_text"] = int(df.duplicated(subset="text").sum())

    df["clean_text"] = [clean_text(t) for t in df["text"]]
    no_content = df["clean_text"].eq("")
    report["empty_after_cleaning"] = int(no_content.sum())
    df = df[~no_content]

    # Same cleaned text with *different* labels: the annotators disagreed, so we cannot
    # trust either label. Drop every copy. Same text with the same label: keep one copy.
    labels_per_text = df.groupby("clean_text")["label"].transform("nunique")
    conflicting = labels_per_text > 1
    report["conflicting_label_duplicates_dropped"] = int(conflicting.sum())
    df = df[~conflicting]

    dup_clean = df.duplicated(subset="clean_text")
    report["duplicate_clean_text_dropped"] = int(dup_clean.sum())
    df = df[~dup_clean].reset_index(drop=True)

    report["rows_final"] = len(df)
    return df, report


def prepare_airline() -> tuple[pd.DataFrame, dict]:
    raw = load_airline_raw()
    repaired = raw["text"].astype(str).map(repair_airline_artifacts)
    artifacts_repaired = int((repaired != raw["text"].astype(str)).sum())
    df, report = prepare(raw.assign(text=repaired), text_col="text", label_col="airline_sentiment")
    report = {"rows_raw": report.pop("rows_raw"), "text_artifacts_repaired": artifacts_repaired, **report}
    df = df.rename(columns={"airline_sentiment_confidence": "label_confidence"})
    keep = ["tweet_id", "text", "clean_text", "label", "label_confidence", "airline", "negativereason", "tweet_created"]
    return df[keep], report


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified split: train and test keep the same positive/negative/neutral proportions."""
    train, test = train_test_split(
        df, test_size=config.TEST_SIZE, stratify=df["label"], random_state=config.RANDOM_STATE
    )
    return train.reset_index(drop=True), test.reset_index(drop=True)
