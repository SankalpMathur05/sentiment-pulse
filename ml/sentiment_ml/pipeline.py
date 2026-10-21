"""Run the whole ML workflow end to end, deterministically.

    python -m sentiment_ml.pipeline

1. load + validate + clean + de-duplicate the raw CSV        (data.py)
2. stratified train/test split, saved to data/processed/     (data.py)
3. exploratory data analysis -> reports/eda.md               (eda.py)
4. model comparison + cleaning ablation with 5-fold CV       (experiments.py)
5. fit the selected model on the full train split
6. evaluate ONCE on the held-out test split                   (evaluate.py)
7. error analysis on the test mistakes                        (error_analysis.py)
8. save versioned artifact -> artifacts/models/<name>-<semver>/
9. write reports/evaluation.md
"""
from __future__ import annotations

import platform
import time
from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np
import sklearn
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline

from . import config, eda, evaluate, experiments
from .artifacts import save_model
from .data import AIRLINE, load_airline_raw, load_tweeteval, prepare, prepare_airline, split
from .error_analysis import misclassified, pair_counts, sample_errors, tag_counts
from .explain import top_features_per_class
from .preprocessing import DEFAULT_CONFIG, PREPROCESSING_VERSION, TextCleaner
from .reporting import md_table, pct, write_markdown

LIMITATIONS = [
    "Trained on about 11k English tweets to six US airlines from February 2015. Language, slang, brands and "
    "platform conventions have changed since, and other industries talk about different things.",
    "A bag-of-words model counts words and short phrases; it does not understand meaning. Sarcasm "
    "(\"great, another delay\"), irony and long-range negation are frequently misread.",
    "Mixed posts (praise + complaint) are forced into a single label; there is no 'mixed' class.",
    "Labels come from crowd annotators and are noisy: about a quarter of tweets have annotator "
    "confidence below 1.0, which limits the accuracy any model can reach.",
    "Confidence scores are estimates. Balanced class weights shift probabilities towards the minority "
    "classes, so they are not perfectly calibrated.",
    "Neutral is the hardest class: it is a mix of questions, information and mild opinions.",
    "Performance drops sharply on general (non-airline) tweets (see the domain-shift check), so the model "
    "should be re-trained or at least re-evaluated before use on another brand or domain.",
]


def build_final_pipeline(logreg_params: dict) -> Pipeline:
    tfidf_params = {k.removeprefix("tfidf__"): v for k, v in logreg_params.items() if k.startswith("tfidf__")}
    clf_params = {k.removeprefix("clf__"): v for k, v in logreg_params.items() if k.startswith("clf__")}
    return Pipeline([
        ("clean", TextCleaner.from_config(DEFAULT_CONFIG)),
        ("tfidf", experiments.make_vectorizer(**tfidf_params)),
        ("clf", experiments.make_logreg(**clf_params)),
    ])


def main() -> None:
    started = time.perf_counter()
    print("1/7 Loading and cleaning data")
    raw = load_airline_raw()
    df, cleaning_report = prepare_airline()
    train, test = split(df)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    train.to_csv(config.PROCESSED_DIR / "train.csv", index=False)
    test.to_csv(config.PROCESSED_DIR / "test.csv", index=False)

    print("2/7 Exploratory data analysis")
    eda.run(raw, df, train, test, cleaning_report)

    print("3/7 Comparing models with 5-fold cross-validation (train split only)")
    comparison = experiments.compare_models(train)
    results = comparison["results"]
    logreg_params = results["logreg"]["best_params"]

    print("4/7 Cleaning ablation")
    ablation = experiments.cleaning_ablation(train, logreg_params)

    print("5/7 Training the final model and evaluating on the held-out test split")
    final = build_final_pipeline(logreg_params).fit(train["text"], train["label"])
    y_pred = final.predict(test["text"])
    proba = final.predict_proba(test["text"])
    labels = [str(c) for c in final.classes_]
    metrics = evaluate.classification_metrics(test["label"], y_pred, proba, labels)

    for key, result in results.items():
        predictions = result["estimator"].predict(test["clean_text"])
        result["test_macro_f1"] = float(f1_score(test["label"], predictions, average="macro"))
        result["test_accuracy"] = float(accuracy_score(test["label"], predictions))

    confidence = proba.max(axis=1)
    calibration = evaluate.calibration_table(test["label"], y_pred, confidence)
    agreement = evaluate.accuracy_by_label_agreement(test, y_pred)
    domain_shift = _domain_shift(final)

    print("6/7 Error analysis")
    clf, feature_names = final.named_steps["clf"], final.named_steps["tfidf"].get_feature_names_out()
    errors = misclassified(test, y_pred, proba, clf, feature_names)

    print("7/7 Saving artifact and reports")
    comparison_rows = [{"model": r["model"], "cv_macro_f1": round(r["cv_macro_f1"], 4),
                        "cv_macro_f1_std": round(r["cv_macro_f1_std"], 4),
                        "test_macro_f1": round(r["test_macro_f1"], 4), "test_accuracy": round(r["test_accuracy"], 4),
                        "selected": r["selected"]} for r in results.values()]
    metadata = {
        "name": config.MODEL_NAME,
        "semver": config.MODEL_SEMVER,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "preprocessing_version": PREPROCESSING_VERSION,
        "random_state": config.RANDOM_STATE,
        "labels": labels,
        "cleaning_config": asdict(DEFAULT_CONFIG),
        "hyperparameters": {k: (list(v) if isinstance(v, tuple) else v) for k, v in logreg_params.items()},
        "dataset": {
            "name": AIRLINE.name, "url": AIRLINE.url, "homepage": AIRLINE.homepage, "licence": AIRLINE.licence,
            "sha256": AIRLINE.sha256, "rows_raw": cleaning_report["rows_raw"],
            "rows_after_cleaning": cleaning_report["rows_final"], "rows_train": len(train), "rows_test": len(test),
            "cleaning_report": cleaning_report,
            "label_distribution_train": {k: int(v) for k, v in train["label"].value_counts().items()},
        },
        "metrics": _rounded(metrics),
        "comparison": comparison_rows,
        "top_features": top_features_per_class(clf, feature_names),
        "limitations": LIMITATIONS,
    }
    out_dir = config.ARTIFACTS_DIR / f"{config.MODEL_NAME}-{config.MODEL_SEMVER}"
    metadata = save_model(final, metadata, out_dir)

    _write_evaluation_report(metadata, comparison, ablation, calibration, agreement, domain_shift, errors, test)
    print(f"\nDone in {time.perf_counter() - started:.0f}s. Model version: {metadata['version']}")
    print(f"Test macro-F1 = {metrics['macro_f1']:.4f} | accuracy = {metrics['accuracy']:.4f}")


def _domain_shift(final: Pipeline) -> dict | None:
    """Score the airline model on general tweets (TweetEval test split) to measure domain shift."""
    try:
        tweeteval = load_tweeteval()
    except Exception as exc:  # network problems must not break training
        print(f"  (skipping domain-shift check: {exc})")
        return None
    te_test = tweeteval[tweeteval["source_split"] == "test"]
    te_test, _ = prepare(te_test, text_col="text", label_col="label")
    predictions = final.predict(te_test["text"])
    return {"rows": len(te_test), "macro_f1": float(f1_score(te_test["label"], predictions, average="macro")),
            "accuracy": float(accuracy_score(te_test["label"], predictions))}


def _rounded(value):
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {k: _rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rounded(v) for v in value]
    return value


def _write_evaluation_report(metadata, comparison, ablation, calibration, agreement, domain_shift, errors, test):
    m = metadata["metrics"]
    results = comparison["results"]
    dummy = results["dummy"]
    train_dist = metadata["dataset"]["label_distribution_train"]
    majority_share = max(train_dist.values()) / sum(train_dist.values())
    cm_fig = evaluate.plot_confusion_matrix(m["confusion_matrix"], "Confusion matrix (test set)", "confusion_matrix.png")
    cal_fig = evaluate.plot_calibration(calibration, "calibration.png")

    lines = [
        "# Evaluation Report",
        "",
        f"Model **{metadata['version']}**, generated by `python -m sentiment_ml.pipeline` "
        f"(seed {config.RANDOM_STATE}, scikit-learn {metadata['sklearn_version']}).",
        "",
        "## 1. Headline",
        "",
        f"- **Macro-F1 on the held-out test set: {m['macro_f1']:.3f}** (accuracy {m['accuracy']:.3f}).",
        f"- A dummy model that always predicts the majority class scores macro-F1 {dummy['test_macro_f1']:.3f} "
        f"with accuracy {dummy['test_accuracy']:.3f}. Its high accuracy shows why accuracy alone is misleading "
        "on imbalanced data.",
        "- **Why macro-F1 is the headline metric:** it averages F1 over the three classes with equal weight, so the "
        f"model cannot score well by doing well only on the {majority_share:.0%} negative majority. "
        "F1 itself balances precision "
        "(when it says positive, is it right?) and recall (does it find the positive posts?).",
        "",
        "## 2. Setup",
        "",
        f"- Data: {metadata['dataset']['rows_raw']:,} raw tweets → {metadata['dataset']['rows_after_cleaning']:,} after "
        f"validation and de-duplication (see `reports/eda.md`).",
        f"- Stratified split: {metadata['dataset']['rows_train']:,} train / {metadata['dataset']['rows_test']:,} test, "
        "made before any vectoriser was fitted.",
        f"- All model and cleaning choices were made with {config.CV_FOLDS}-fold stratified cross-validation on the "
        "train split (scoring: macro-F1). The test split was used once, for this report.",
        f"- Selection rule: serve Logistic Regression unless another candidate beats it by more than "
        f"{experiments.SELECTION_TOLERANCE} CV macro-F1 (Logistic Regression provides real probabilities and exact "
        "per-word explanations).",
        "",
        "## 3. Model comparison",
        "",
    ]
    lines += md_table(
        ["Model", "CV macro-F1 (mean ± std)", "Test macro-F1", "Test accuracy", "Best settings", "Served"],
        [[r["model"], f"{r['cv_macro_f1']:.3f} ± {r['cv_macro_f1_std']:.3f}", f"{r['test_macro_f1']:.3f}",
          f"{r['test_accuracy']:.3f}", _params(r["best_params"]), "✅" if r["selected"] else ""]
         for r in results.values()])
    if comparison["best_overall"] != comparison["selected"]:
        lines += ["", f"The best CV score belongs to **{results[comparison['best_overall']]['model']}**, "
                  f"{comparison['gap_to_best']:.3f} above Logistic Regression, which is within the tolerance, "
                  "so Logistic Regression is served for its probabilities and explainability."]

    cw = results["logreg"]["class_weight_comparison"]
    lines += ["", "## 4. Class imbalance", "",
              "Logistic Regression was tuned with and without balanced class weights "
              "(balanced = mistakes on rare classes cost more during training):", ""]
    lines += md_table(["Class weights", "Best CV macro-F1"],
                      [[k, f"{v['cv_macro_f1']:.3f} ± {v['cv_macro_f1_std']:.3f}"] for k, v in cw.items()])
    chosen_cw = metadata["hyperparameters"].get("clf__class_weight")
    lines += ["", f"Selected: **{chosen_cw or 'none'}**. We use class weights rather than resampling: no "
              "duplicated or synthetic tweets, nothing extra to explain, and the effect is visible in "
              "minority-class recall below."]

    lines += ["", "## 5. Cleaning ablation (which cleaning steps help or hurt?)", "",
              "Each row changes ONE cleaning step and re-runs 5-fold CV with the selected model settings.", ""]
    lines += md_table(["Change", "CV macro-F1", "Δ vs. production"],
                      [[a["description"], f"{a['cv_macro_f1']:.4f} ± {a['cv_macro_f1_std']:.4f}",
                        "–" if a["step"] == "baseline" else f"{a['delta']:+.4f}"] for a in ablation])
    lines += ["", "Δ values smaller than the CV standard deviation are within noise. Steps are kept for a "
              "principled reason even when their measured effect is small (see the README's cleaning table)."]

    lines += ["", "## 6. Test-set results (served model)", "", f"![Confusion matrix]({cm_fig})", ""]
    lines += md_table(["Class", "Precision", "Recall", "F1", "Support"],
                      [[lbl, f"{v['precision']:.3f}", f"{v['recall']:.3f}", f"{v['f1']:.3f}", v["support"]]
                       for lbl, v in m["per_class"].items()])
    lines += [""] + md_table(["Average", "Precision", "Recall", "F1"],
                             [["macro", f"{m['macro_precision']:.3f}", f"{m['macro_recall']:.3f}", f"{m['macro_f1']:.3f}"],
                              ["weighted", "–", "–", f"{m['weighted_f1']:.3f}"]])
    lines += ["", "Rows of the confusion matrix are the true labels and columns the predictions; the percentage "
              "is the share of that true class."]

    low = [r for r in calibration if r["mean_confidence"] < 0.55]
    lines += ["", "## 7. Confidence: can we trust the score?", "", f"![Calibration]({cal_fig})", ""]
    lines += md_table(["Confidence band", "Predictions", "Share", "Avg confidence", "Actual accuracy"],
                      [[r["band"], r["count"], pct(r["share"]), f"{r['mean_confidence']:.2f}", pct(r["accuracy"])]
                       for r in calibration])
    lines += ["", f"Log loss {m['log_loss']:.3f}, multi-class Brier score {m['brier_score']:.3f} (lower is better). "
              "Higher confidence does mean higher accuracy, but the values are estimates, which is why the UI labels "
              "them as such and flags predictions below 0.55 as low confidence"
              + (f" ({sum(r['count'] for r in low):,} test posts)." if low else ".")]

    lines += ["", "## 8. Label noise", "",
              "Accuracy of the served model grouped by how much the human annotators agreed:", ""]
    lines += md_table(["Annotator agreement", "Test tweets", "Model accuracy"],
                      [[r["band"], r["count"], pct(r["accuracy"])] for r in agreement])
    lines += ["", "When humans disagree, the 'correct' answer is uncertain too; part of the error rate is label noise "
              "rather than model failure."]

    if domain_shift:
        lines += ["", "## 9. Domain shift check", "",
                  f"The same model scored on {domain_shift['rows']:,} general tweets (TweetEval sentiment test split, "
                  f"SemEval-2017): **macro-F1 {domain_shift['macro_f1']:.3f}**, accuracy {domain_shift['accuracy']:.3f}. "
                  "Performance falls substantially outside the airline domain. This is the clearest evidence "
                  "for the model's main limitation."]

    lines += ["", "## 10. Error analysis", "",
              f"{len(errors):,} of {len(test):,} test tweets are misclassified ({len(errors) / len(test):.1%}).", "",
              "### Which mistakes are most common?", ""]
    lines += md_table(["True → predicted", "Errors"], pair_counts(errors))
    lines += ["", "### Heuristic pattern tags across all errors", "",
              "(A tweet can have several tags. Tags suggest a reason; the reviewed examples below confirm them.)", ""]
    lines += md_table(["Pattern", "Errors", "Share of errors"], tag_counts(errors))
    sample = sample_errors(errors)
    lines += ["", f"### {len(sample)} most confident mistakes (up to 4 per error type)", ""]
    lines += md_table(["True", "Predicted", "Confidence", "Label agreement", "Tweet", "Tags"],
                      [[r.label, r.predicted, f"{r.confidence:.2f}", f"{r.label_confidence:.2f}", _escape(r.text),
                        ", ".join(r.tags)] for r in sample.itertuples()])
    notes = config.REPORTS_DIR / "error_analysis_notes.md"
    if notes.exists():
        lines += ["", notes.read_text(encoding="utf-8").strip()]

    lines += ["", "## 11. Limitations", ""] + [f"- {item}" for item in metadata["limitations"]]
    lines += ["", "## 12. Reproduce", "", "```bash", "pip install -e \"ml[train]\"", "python -m sentiment_ml.pipeline",
              "```", "", "Same seed, same data checksum and pinned library versions give the same metrics."]
    write_markdown(config.REPORTS_DIR / "evaluation.md", lines)


def _params(params: dict) -> str:
    return ", ".join(f"{k.split('__')[-1]}={v}" for k, v in params.items()) or "–"


def _escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    np.random.seed(config.RANDOM_STATE)
    main()
