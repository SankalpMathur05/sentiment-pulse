import pandas as pd

from sentiment_ml import config
from sentiment_ml.data import prepare, repair_airline_artifacts, split


def test_repair_reverses_find_and_replace_artifacts():
    assert repair_airline_artifacts("my flight was Cancelled Flightled") == "my flight was cancelled"
    assert repair_airline_artifacts("reFlight Booking Problems me Late Flightr") == "rebook me later"
    assert repair_airline_artifacts("chocoLate Flight cake") == "chocolate cake"


def _frame(rows):
    return pd.DataFrame(rows, columns=["tweet_id", "text", "label"])


def test_prepare_drops_invalid_rows_and_conflicting_duplicates():
    df = _frame([
        (1, "great flight", "positive"),
        (2, "  ", "positive"),  # empty text
        (3, "lost my bag", "angry"),  # invalid label
        (4, "@united so late", "negative"),
        (5, "@delta so late", "neutral"),  # same cleaned text, different label -> both dropped
        (6, "great flight!!", "positive"),
        (7, "Great   flight!", "positive"),  # same cleaned text, same label -> one kept
        (1, "great flight", "positive"),  # duplicate tweet id
    ])
    clean, report = prepare(df, text_col="text", label_col="label")
    assert report["empty_text"] == 1
    assert report["invalid_label"] == 1
    assert report["duplicate_tweet_id"] == 1
    assert report["conflicting_label_duplicates_dropped"] == 2
    assert report["duplicate_clean_text_dropped"] == 1
    assert sorted(clean["clean_text"]) == ["great flight", "great flight !"]
    assert report["rows_final"] == len(clean)


def test_split_is_stratified_disjoint_and_deterministic():
    labels = ["negative"] * 60 + ["neutral"] * 25 + ["positive"] * 15
    df = pd.DataFrame({"text": [f"tweet {i}" for i in range(100)], "clean_text": [f"tweet {i}" for i in range(100)],
                       "label": labels})
    train, test = split(df)
    assert len(test) == int(len(df) * config.TEST_SIZE)
    assert set(train["text"]).isdisjoint(test["text"])  # no leakage between splits
    assert test["label"].value_counts().to_dict() == {"negative": 12, "neutral": 5, "positive": 3}
    train_again, test_again = split(df)
    assert test["text"].tolist() == test_again["text"].tolist()  # same seed, same split
