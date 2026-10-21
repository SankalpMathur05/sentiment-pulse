import pytest

from sentiment_ml.preprocessing import CleaningConfig, TextCleaner, clean_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("@united thanks", "<user> thanks"),
        ("see http://t.co/abc and www.example.com", "see <url> and <url>"),
        ("#NeverAgain #fail", "never again fail"),
        ("I love it :) but :( later", "i love it <smile> but <sad> later"),
        ("so happy 😍", "so happy :smiling_face_with_heart-eyes:"),
        ("soooo goooood", "soo good"),
        ("WHY?!!!", "why ? !"),
        ("&amp; &lt;3", "<heart>"),
        ("   lots    of\n\nspace  ", "lots of space"),
    ],
)
def test_clean_text_examples(raw, expected):
    assert clean_text(raw) == expected


def test_negations_and_contractions_are_kept():
    # Stop-word lists usually delete these, which would flip the meaning of the post.
    cleaned = clean_text("This is not good, I don't like it and never will")
    for word in ("not", "don't", "never"):
        assert word in cleaned.split()


def test_times_are_not_mistaken_for_emoticons():
    assert "<" not in clean_text("Boarding at 10:30 (gate 4):")


def test_cleaning_is_idempotent():
    once = clean_text("@united WHY is my flight sooo late?!! 😡 #fail http://t.co/x")
    assert clean_text(once) == once


@pytest.mark.parametrize("value", ["", "   ", None, 42])
def test_empty_or_non_string_input_returns_empty_string(value):
    assert clean_text(value) == ""


def test_config_flags_switch_steps_off():
    text = "@united :( 😡 #fail!"
    assert "<user>" not in clean_text(text, CleaningConfig(replace_mentions=False))
    assert "<sad>" not in clean_text(text, CleaningConfig(convert_emoticons=False))
    assert ":enraged_face:" not in clean_text(text, CleaningConfig(convert_emoji=False))
    assert "fail" not in clean_text(text, CleaningConfig(keep_hashtag_words=False))
    assert "!" not in clean_text(text, CleaningConfig(keep_exclaim_question=False))


def test_negation_marking_is_scoped():
    assert clean_text("not good at all ! fine", CleaningConfig(mark_negation=True)) == "not neg_good neg_at neg_all ! fine"


def test_text_cleaner_transformer_matches_function():
    texts = ["@delta great crew!", "flight delayed :("]
    assert TextCleaner().fit(texts).transform(texts) == [clean_text(t) for t in texts]
