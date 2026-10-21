import json

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from sentiment_ml.artifacts import save_model
from sentiment_ml.inference import SentimentModel
from sentiment_ml.preprocessing import TextCleaner, tokenize

TEXTS = [
    ("love the crew, great flight", "positive"), ("thank you so much, amazing service", "positive"),
    ("best airline ever", "positive"), ("great job, loved it", "positive"),
    ("flight delayed again, awful", "negative"), ("lost my bag, terrible service", "negative"),
    ("worst airline, cancelled again", "negative"), ("rude staff and late flight", "negative"),
    ("what time does boarding start?", "neutral"), ("is there wifi on flight 12?", "neutral"),
    ("which gate for the flight to boston?", "neutral"), ("do you fly to denver?", "neutral"),
]


@pytest.fixture(scope="module")
def model_dir(tmp_path_factory):
    pipeline = Pipeline([
        ("clean", TextCleaner()),
        ("tfidf", TfidfVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ]).fit([t for t, _ in TEXTS], [label for _, label in TEXTS])
    out = tmp_path_factory.mktemp("model")
    save_model(pipeline, {"name": "test-model", "semver": "0.0.1"}, out)
    return out


def test_round_trip_and_version_contains_checksum(model_dir):
    model = SentimentModel.load(model_dir)
    metadata = json.loads((model_dir / "metadata.json").read_text())
    assert model.version == f"test-model@0.0.1+{metadata['artifact_sha256'][:8]}"


def test_prediction_shape_and_probabilities(model_dir):
    prediction = SentimentModel.load(model_dir).predict("awful flight, lost my bag")
    assert prediction.sentiment == "negative"
    assert set(prediction.probabilities) == {"negative", "neutral", "positive"}
    assert sum(prediction.probabilities.values()) == pytest.approx(1.0, abs=1e-3)
    assert prediction.confidence == max(prediction.probabilities.values())


def test_explanation_words_come_from_the_post(model_dir):
    prediction = SentimentModel.load(model_dir).predict("awful flight, lost my bag")
    assert prediction.top_words
    cleaned_tokens = "awful flight lost my bag"
    assert all(word["token"] in cleaned_tokens for word in prediction.top_words)
    assert all(word["weight"] > 0 for word in prediction.top_words)


def test_normalize_matches_what_the_model_sees(model_dir):
    model = SentimentModel.load(model_dir)
    assert model.normalize("  @united   GREAT flight!!! ") == model.normalize("@delta great flight!")


def test_tampered_model_file_is_rejected(model_dir, tmp_path):
    for name in ("model.joblib", "metadata.json"):
        (tmp_path / name).write_bytes((model_dir / name).read_bytes())
    with (tmp_path / "model.joblib").open("ab") as fh:
        fh.write(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        SentimentModel.load(tmp_path)
