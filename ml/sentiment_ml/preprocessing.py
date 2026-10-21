"""Social-media text cleaning, shared by training and the API.

The model never sees raw text. Every post goes through `clean_text` first, both
during training and when the API predicts. Keeping a single implementation
guarantees the model is always served text in exactly the format it learned from
(no "training/serving skew").

Each step below notes the sentiment signal it could destroy and how we protect it.
The `CleaningConfig` flags let `experiments.py` switch steps off one at a time and
measure their effect with cross-validation (the cleaning ablation study).
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import asdict, dataclass, fields

import emoji
from sklearn.base import BaseEstimator, TransformerMixin

# Bump this whenever cleaning behaviour changes: it is stored in the model metadata
# and becomes part of the cache key, so old cached predictions are never reused.
PREPROCESSING_VERSION = "1.0"

URL_TOKEN = "<url>"
USER_TOKEN = "<user>"

_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_MENTION_RE = re.compile(r"@\w+")
_HASHTAG_RE = re.compile(r"#(\w+)")
_CAMEL_CASE_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")

# Text emoticons -> named tokens. Applied before punctuation is stripped, otherwise
# ":(" would simply disappear. Order matters: more specific patterns come first.
_EMOTICONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"</3"), " <brokenheart> "),
    (re.compile(r"<3+"), " <heart> "),
    (re.compile(r"(?<![\w:])[:=]-?D\b|\b[xX]-?D\b"), " <laugh> "),
    (re.compile(r"(?<![\w:]);-?[)D]"), " <wink> "),
    (re.compile(r"(?<![\w:])[:=]'?-?[)\]}]+"), " <smile> "),
    (re.compile(r"(?<![\w:])[:=]'?-?[(\[{]+"), " <sad> "),
    (re.compile(r"(?<![\w:])[:=]-?[pP]\b"), " <tongue> "),
    (re.compile(r"(?<![\w:/])[:=]-?[/\\](?![/\\])"), " <skeptical> "),
]

_ELONGATION_RE = re.compile(r"([^\W\d_])\1{2,}")  # "soooo" -> "soo" (letters only)
_REPEAT_PUNCT_RE = re.compile(r"([!?])\1+")  # "!!!" -> "!"

# Final tokenizer: placeholders, emoji names, words (with contractions like "don't"), ! and ?.
_TOKEN_RE = re.compile(r"<[a-z]+>|:[^\s:]+:|[^\W_]+(?:'[^\W_]+)?|[!?]")

_NEGATIONS = {"not", "no", "never", "nothing", "nobody", "none", "nowhere", "neither", "cannot"}
_NEGATION_SCOPE = 3  # how many following words a negation flips


@dataclass(frozen=True)
class CleaningConfig:
    """On/off switches for each cleaning step (all on = the production setting)."""

    replace_urls: bool = True
    replace_mentions: bool = True
    keep_hashtag_words: bool = True
    convert_emoji: bool = True
    convert_emoticons: bool = True
    keep_exclaim_question: bool = True
    squash_elongation: bool = True
    mark_negation: bool = False


DEFAULT_CONFIG = CleaningConfig()


def clean_text(text: str, config: CleaningConfig = DEFAULT_CONFIG) -> str:
    """Turn one raw post into a normalised, space-separated string of tokens."""
    if not isinstance(text, str):
        return ""

    # 1. Decode HTML entities ("&amp;" -> "&", "&lt;3" -> "<3") and normalise Unicode
    #    (fancy bold letters, full-width characters). Signal risk: none.
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text).replace("\u2019", "'").replace("\u2018", "'")

    # 2. URLs carry no sentiment and would add random tokens like "t", "co", "x7fq".
    #    Signal risk: none. We keep a placeholder so "has a link" is still visible.
    if config.replace_urls:
        text = _URL_RE.sub(f" {URL_TOKEN} ", text)

    # 3. @mentions identify the brand or person, not the feeling. Keeping them would let
    #    the model learn "@united = negative", a shortcut that fails for other brands.
    #    Signal risk: low (the handle itself is not sentiment).
    if config.replace_mentions:
        text = _MENTION_RE.sub(f" {USER_TOKEN} ", text)

    # 4. Hashtags often ARE sentiment ("#fail", "#LoveThisAirline"): keep the words, drop
    #    the "#", and split CamelCase. Signal risk: deleting hashtags would lose real signal.
    if config.keep_hashtag_words:
        text = _HASHTAG_RE.sub(lambda m: " " + _CAMEL_CASE_RE.sub(" ", m.group(1)) + " ", text)
    else:
        text = _HASHTAG_RE.sub(" ", text)

    # 5. Emoticons such as ":(" are strong sentiment cues made of punctuation. Convert
    #    them to tokens before punctuation is stripped. Signal risk: HIGH if not converted.
    if config.convert_emoticons:
        for pattern, token in _EMOTICONS:
            text = pattern.sub(token, text)

    # 6. Emojis -> their names (":face_with_tears_of_joy:"), so each emoji becomes one
    #    token. Signal risk: HIGH if removed, so we convert instead of deleting.
    if config.convert_emoji:
        text = emoji.demojize(text, delimiters=(" :", ": "))
    else:
        text = emoji.replace_emoji(text, replace=" ")

    # 7. Lowercase: "GREAT" and "great" mean the same thing to a bag-of-words model.
    #    Signal risk: shouting in CAPS is lost (accepted trade-off, documented).
    text = text.lower()

    # 8. Elongation: "soooo goooood" -> "soo good" (keep 2 letters so "soo" still differs
    #    from "so", but all spellings of the stretch collapse into one). "!!!" -> "!".
    if config.squash_elongation:
        text = _ELONGATION_RE.sub(r"\1\1", text)
    text = _REPEAT_PUNCT_RE.sub(r"\1", text)

    # 9. Tokenise: keep words, contractions ("don't", "isn't" = negation!), placeholders,
    #    emoji names and "!"/"?". All other punctuation is dropped.
    #    NOTE: we do NOT remove stop words. Standard stop-word lists delete "not", "no"
    #    and "never", which would flip "not good" into "good".
    tokens = _TOKEN_RE.findall(text)
    if not config.keep_exclaim_question:
        tokens = [t for t in tokens if t not in {"!", "?"}]

    # 10. Optional negation marking: "not good at all" -> "not neg_good neg_at neg_all".
    #     Off by default; kept only if cross-validation shows it helps.
    if config.mark_negation:
        tokens = _mark_negation(tokens)

    return " ".join(tokens)


def _mark_negation(tokens: list[str]) -> list[str]:
    marked: list[str] = []
    remaining = 0
    for token in tokens:
        if token in {"!", "?"} or token.startswith("<"):
            remaining = 0
            marked.append(token)
        elif remaining > 0:
            marked.append(f"neg_{token}")
            remaining -= 1
        else:
            marked.append(token)
        if token in _NEGATIONS or token.endswith("n't"):
            remaining = _NEGATION_SCOPE
    return marked


def tokenize(cleaned: str) -> list[str]:
    """Split already-cleaned text into tokens (used by the TF-IDF vectoriser)."""
    return cleaned.split()


class TextCleaner(BaseEstimator, TransformerMixin):
    """scikit-learn wrapper so cleaning is the first step of the saved model pipeline.

    Cleaning is stateless: `fit` learns nothing, so it cannot leak test information.
    """

    def __init__(
        self,
        replace_urls: bool = True,
        replace_mentions: bool = True,
        keep_hashtag_words: bool = True,
        convert_emoji: bool = True,
        convert_emoticons: bool = True,
        keep_exclaim_question: bool = True,
        squash_elongation: bool = True,
        mark_negation: bool = False,
    ) -> None:
        self.replace_urls = replace_urls
        self.replace_mentions = replace_mentions
        self.keep_hashtag_words = keep_hashtag_words
        self.convert_emoji = convert_emoji
        self.convert_emoticons = convert_emoticons
        self.keep_exclaim_question = keep_exclaim_question
        self.squash_elongation = squash_elongation
        self.mark_negation = mark_negation

    @property
    def config(self) -> CleaningConfig:
        return CleaningConfig(**{f.name: getattr(self, f.name) for f in fields(CleaningConfig)})

    @classmethod
    def from_config(cls, config: CleaningConfig) -> "TextCleaner":
        return cls(**asdict(config))

    def fit(self, X, y=None):  # noqa: N803 (scikit-learn naming convention)
        return self

    def transform(self, X):  # noqa: N803
        config = self.config
        return [clean_text(text, config) for text in X]
