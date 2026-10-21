"""Model selection and cleaning ablation, using cross-validation on the TRAIN split only.

The test split is never touched here. Every decision (which model, which settings,
which cleaning steps) is made from 5-fold cross-validated macro-F1 on train data.

Cleaning is stateless (it learns nothing from the data), so we clean the texts once up
front. The TF-IDF vectoriser DOES learn (vocabulary + IDF weights), so it sits inside
each cross-validation pipeline and is re-fitted on every training fold.
"""
from __future__ import annotations

from dataclasses import asdict, replace

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from . import config
from .preprocessing import DEFAULT_CONFIG, CleaningConfig, clean_text, tokenize

# Serve Logistic Regression unless another model beats it by more than this in CV
# macro-F1. LogReg gives real probabilities (needed for the confidence score) and
# exact per-word explanations, which are worth a tiny amount of accuracy.
SELECTION_TOLERANCE = 0.01


def make_vectorizer(**overrides) -> TfidfVectorizer:
    params = dict(tokenizer=tokenize, token_pattern=None, lowercase=False, sublinear_tf=True,
                  ngram_range=(1, 2), min_df=2)
    params.update(overrides)
    return TfidfVectorizer(**params)


def make_logreg(**overrides) -> LogisticRegression:
    params = dict(C=1.0, class_weight="balanced", max_iter=3000, random_state=config.RANDOM_STATE)
    params.update(overrides)
    return LogisticRegression(**params)


def candidates() -> dict[str, tuple[str, Pipeline, dict]]:
    """name -> (display name, pipeline, hyper-parameter grid)."""
    char_union = FeatureUnion([
        ("word", make_vectorizer()),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True, lowercase=False)),
    ])
    return {
        "dummy": ("Dummy (always majority class)",
                  Pipeline([("tfidf", make_vectorizer()), ("clf", DummyClassifier(strategy="most_frequent"))]), {}),
        "complement_nb": ("TF-IDF + Complement Naive Bayes",
                          Pipeline([("tfidf", make_vectorizer()), ("clf", ComplementNB())]),
                          {"clf__alpha": [0.1, 0.3, 1.0], "tfidf__ngram_range": [(1, 1), (1, 2)]}),
        "linear_svm": ("TF-IDF + Linear SVM",
                       Pipeline([("tfidf", make_vectorizer()),
                                 ("clf", LinearSVC(class_weight="balanced", random_state=config.RANDOM_STATE))]),
                       {"clf__C": [0.05, 0.1, 0.3, 1.0], "tfidf__ngram_range": [(1, 1), (1, 2)]}),
        "logreg": ("TF-IDF + Logistic Regression",
                   Pipeline([("tfidf", make_vectorizer()), ("clf", make_logreg())]),
                   {"clf__C": [0.5, 1.0, 2.0, 4.0, 8.0], "clf__class_weight": [None, "balanced"],
                    "tfidf__ngram_range": [(1, 1), (1, 2)], "tfidf__min_df": [1, 2]}),
        "logreg_word_char": ("TF-IDF words + character n-grams + Logistic Regression",
                             Pipeline([("tfidf", char_union), ("clf", make_logreg())]),
                             {"clf__C": [1.0, 2.0, 4.0]}),
    }


def cv_splitter() -> StratifiedKFold:
    return StratifiedKFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=config.RANDOM_STATE)


def compare_models(train: pd.DataFrame) -> dict:
    """Grid-search every candidate with 5-fold CV and pick the model to serve."""
    X, y = train["clean_text"], train["label"]
    results = {}
    for key, (display, pipeline, grid) in candidates().items():
        search = GridSearchCV(pipeline, grid or {}, scoring="f1_macro", cv=cv_splitter(), n_jobs=-1)
        search.fit(X, y)
        best = search.best_index_
        results[key] = {
            "model": display,
            "best_params": dict(search.best_params_),
            "cv_macro_f1": float(search.cv_results_["mean_test_score"][best]),
            "cv_macro_f1_std": float(search.cv_results_["std_test_score"][best]),
            "estimator": search.best_estimator_,
        }
        if key == "logreg":
            results[key]["class_weight_comparison"] = _best_score_per_class_weight(search)
        print(f"  {display:<55} CV macro-F1 = {results[key]['cv_macro_f1']:.4f} ± {results[key]['cv_macro_f1_std']:.4f}")

    best_overall = max(results, key=lambda k: results[k]["cv_macro_f1"])
    gap = results[best_overall]["cv_macro_f1"] - results["logreg"]["cv_macro_f1"]
    selected = "logreg" if gap <= SELECTION_TOLERANCE else best_overall
    for key in results:
        results[key]["selected"] = key == selected
    return {"results": results, "selected": selected, "best_overall": best_overall, "gap_to_best": gap}


def _best_score_per_class_weight(search: GridSearchCV) -> dict:
    cv = pd.DataFrame(search.cv_results_)
    cv["class_weight"] = cv["param_clf__class_weight"].map(lambda v: "balanced" if v == "balanced" else "none")
    best = cv.sort_values("mean_test_score", ascending=False).groupby("class_weight").first()
    return {cw: {"cv_macro_f1": float(row.mean_test_score), "cv_macro_f1_std": float(row.std_test_score)}
            for cw, row in best.iterrows()}


ABLATIONS: dict[str, tuple[str, dict]] = {
    "replace_urls": ("Keep raw URLs instead of `<url>`", {"replace_urls": False}),
    "replace_mentions": ("Keep @mentions (brand handles) instead of `<user>`", {"replace_mentions": False}),
    "keep_hashtag_words": ("Delete hashtags instead of keeping their words", {"keep_hashtag_words": False}),
    "convert_emoji": ("Delete emojis instead of converting them to names", {"convert_emoji": False}),
    "convert_emoticons": ("Delete text emoticons like :) instead of converting", {"convert_emoticons": False}),
    "keep_exclaim_question": ("Delete ! and ?", {"keep_exclaim_question": False}),
    "squash_elongation": ("Keep elongations (sooo) as-is", {"squash_elongation": False}),
    "mark_negation": ("ADD negation marking (not good -> not neg_good)", {"mark_negation": True}),
}


def cleaning_ablation(train: pd.DataFrame, logreg_params: dict) -> list[dict]:
    """Switch each cleaning step off (or on) and measure the change in CV macro-F1."""
    def score(cleaning: CleaningConfig) -> tuple[float, float]:
        texts = [clean_text(t, cleaning) for t in train["text"]]
        pipeline = Pipeline([("tfidf", make_vectorizer()), ("clf", make_logreg())]).set_params(**logreg_params)
        scores = cross_val_score(pipeline, texts, train["label"], scoring="f1_macro", cv=cv_splitter(), n_jobs=-1)
        return float(scores.mean()), float(scores.std())

    base_mean, base_std = score(DEFAULT_CONFIG)
    rows = [{"step": "baseline", "description": "Production cleaning (all steps as designed)",
             "cv_macro_f1": base_mean, "cv_macro_f1_std": base_std, "delta": 0.0}]
    variants = dict(ABLATIONS)
    variants["minimal"] = ("Minimal cleaning (lowercase + split only)", {
        **{k: False for k in asdict(DEFAULT_CONFIG)},
    })
    for step, (description, change) in variants.items():
        mean, std = score(replace(DEFAULT_CONFIG, **change))
        rows.append({"step": step, "description": description, "cv_macro_f1": mean, "cv_macro_f1_std": std,
                     "delta": mean - base_mean})
        print(f"  {description:<55} {mean:.4f} ({mean - base_mean:+.4f})")
    return rows
