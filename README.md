# Sentiment Pulse

**An AI-powered social media sentiment dashboard.** It classifies posts as **Positive**, **Negative** or **Neutral** with a model trained from scratch (TF-IDF + Logistic Regression), explains each prediction, stores every prediction in PostgreSQL, caches repeated requests in Redis, and summarises everything in a Next.js dashboard.

| | |
|---|---|
| **Headline result** | Macro-F1 **0.754**, accuracy **0.809** on a held-out test set of 2,847 tweets (majority-class baseline: macro-F1 0.259) |
| **Model** | `tfidf-logreg@1.0.0+9cb76b11`, trained on the Twitter US Airline Sentiment dataset, deterministic (seed 42) |
| **Stack** | Python · scikit-learn · FastAPI · PostgreSQL 16 · Redis 7 · Next.js · Docker Compose |
| **Run it** | `docker compose up --build`, then open http://localhost:3000 |
| **Live demo** | https://sentiment-pulse-tawny.vercel.app (free tier: the first request may take up to a minute while the API wakes up) |
| **Reports** | [Evaluation report](reports/evaluation.md) · [EDA](reports/eda.md) · [Dataset bake-off](reports/dataset_bakeoff.md) |

---

## Contents
1. [Quick start](#1-quick-start)
2. [What it does](#2-what-it-does)
3. [Architecture](#3-architecture)
4. [Dataset](#4-dataset)
5. [Preprocessing](#5-preprocessing)
6. [Model and evaluation](#6-model-and-evaluation)
7. [API](#7-api)
8. [Database design](#8-database-design)
9. [Cache strategy](#9-cache-strategy)
10. [Frontend](#10-frontend)
11. [Configuration](#11-configuration)
12. [Testing and CI](#12-testing-and-ci)
13. [Deployment](#13-deployment)
14. [Design decisions and trade-offs](#14-design-decisions-and-trade-offs)
15. [Known limitations](#15-known-limitations)
16. [Scaling, monitoring and drift](#16-scaling-monitoring-and-drift)
17. [Project structure](#17-project-structure)
18. [Use of AI coding assistants](#18-use-of-ai-coding-assistants)

---

## 1. Quick start

**Prerequisites:** Docker Desktop (or Docker Engine with Compose v2) and Git. Nothing else: Python, Node, PostgreSQL and Redis all run in containers.

```bash
git clone https://github.com/SankalpMathur05/sentiment-pulse.git
cd sentiment-pulse
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:3000 | Dashboard (Analyze, Dashboard, History, Batch, Model) |
| http://localhost:8000/docs | Interactive API documentation (OpenAPI / Swagger) |
| http://localhost:8000/health | Service and dependency health |

The first build takes a few minutes (Python and Node dependencies). The trained model is committed in `artifacts/`, so **nothing is retrained at startup**. On startup the API applies the database migrations (`alembic upgrade head`) and loads the model once.

Every setting has a safe local default, so no `.env` file is needed. To override settings, `cp .env.example .env` and edit it (see [Configuration](#11-configuration)). Stop with `docker compose down`, or `docker compose down -v` to also delete the stored predictions.

### Reproduce the model (optional)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r ml/requirements.txt && pip install -e ml
python -m sentiment_ml.pipeline                         # ~3 minutes on a laptop CPU
```

This re-runs validation, cleaning, the split, EDA, cross-validated model selection, the cleaning ablation, test evaluation and error analysis. It rewrites `reports/` and `artifacts/`. With the pinned versions in `ml/requirements.txt` it reproduces the same model fingerprint (`9cb76b11`) and the same metrics.

### Run the parts locally without Docker (development)

```bash
# PostgreSQL + Redis in Docker, published on localhost:5432 / :6379
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db redis
pip install -r backend/requirements-dev.txt && pip install -e ml
cd backend && alembic upgrade head && uvicorn app.main:app --reload   # API on :8000
cd frontend && npm ci && npm run dev                                  # UI on :3000 (proxies /api to :8000)
```

The API's built-in defaults (`backend/app/config.py`, documented in `backend/.env.example`) already point at `localhost` with the compose credentials, so no extra configuration is needed.

---

## 2. What it does

| Requirement | Where |
|---|---|
| FR-01 Single-post prediction | `POST /api/predict` · **Analyze** page |
| FR-02 Confidence, labelled as an estimate | probabilities for all three classes; "Estimated confidence" in the UI; low-confidence flag below 0.55 |
| FR-03 Prediction history in PostgreSQL | `predictions` table: text, label, scores, model version, cache status, timestamp |
| FR-04 Analytics dashboard | `GET /api/analytics/summary` · **Dashboard** page (totals, distribution, trend, recent table) |
| FR-05 Filters by sentiment and date range | `GET /api/predictions` + `GET /api/analytics/summary` · filter bar on Dashboard and History |
| FR-06 API validation with consistent errors | one JSON error envelope for every failure (see [API](#7-api)) |
| FR-07 Redis caching | key = model version + hash of the normalised text, 24h TTL |
| FR-08 Cache observability | `cache_status` + `X-Cache` header in every response, structured log line, stored per row, dashboard panel |
| FR-09 Health checks | `GET /health` (API, PostgreSQL, Redis, model) and `GET /health/live` |
| Good to have | model comparison (5 models) · CSV batch prediction · CI on GitHub Actions · per-word explanations · cache statistics on the dashboard |

---

## 3. Architecture

```
 Browser ──► Next.js (frontend, :3000) ──/api, /health──► FastAPI (api, :8000) ──► PostgreSQL (predictions)
                 rewrites() proxy                           │   ▲
                                                            │   └── model loaded once at startup
                                                            ▼       from artifacts/models/…
                                                          Redis (prediction cache)
```

**Life of one request (`POST /api/predict`):**
1. Validate: must be a string, stripped, non-empty, ≤ 1000 characters, no extra fields.
2. Normalise the text with the **same `clean_text` used in training**. Reject it if nothing analysable remains.
3. Build the cache key `sentiment:v1:{model_version}:{sha256(normalised text)}` and `GET` it from Redis.
4. **Hit:** reuse the cached result. **Miss:** run the model, then `SET` the result with a TTL (only after success). **Redis down:** run the model with status `bypass`.
5. Insert one row into `predictions` (every request is stored, including hits).
6. Return the label, probabilities, top contributing words, model version, cache status and latency. Log one structured JSON line (no raw text).

The browser only talks to the Next.js server. Next.js `rewrites()` forwards `/api/*` and `/health` to the API (`API_INTERNAL_URL`), so there are no cross-origin (CORS) requests in Docker or on Vercel.

---

## 4. Dataset

| | |
|---|---|
| **Name** | Twitter US Airline Sentiment (CrowdFlower / Figure Eight, *Data for Everyone*) |
| **Source** | https://www.kaggle.com/datasets/crowdflower/twitter-airline-sentiment (credential-free mirror used for download: https://huggingface.co/datasets/osanseviero/twitter-airline-sentiment) |
| **Licence** | CC BY-NC-SA 4.0 (attribution, non-commercial, share-alike). Redistributed unchanged in `data/raw/` with attribution ([data/raw/README.md](data/raw/README.md)) |
| **Size** | 14,640 tweets about 6 US airlines, posted 16–24 February 2015 |
| **Schema** | 15 columns. Used: `text` (input), `airline_sentiment` (label: negative / neutral / positive), `airline_sentiment_confidence` (annotator agreement, for error analysis). Also present: `tweet_id`, `airline`, `negativereason`, `negativereason_confidence`, `tweet_created`, `name`, `retweet_count`, `tweet_location`, `user_timezone`, and mostly-empty `*_gold` and `tweet_coord` columns |
| **Labels** | Already Negative / Neutral / Positive, so no mapping is needed (only lower-cased). Distribution after cleaning: 64% / 21% / 16% |
| **Integrity** | SHA-256 pinned in code (`ea94b23f…f15e`) and verified on every load |

**Why this dataset:**
- It is about customers talking *to brands*, which is LocoBuzz's domain.
- It has native three-class labels.
- It has real class imbalance to handle.
- It carries per-tweet annotator confidence, which made an honest label-noise analysis possible.

It was chosen over TweetEval-sentiment (60k general tweets, CC BY 3.0) after a side-by-side [bake-off](reports/dataset_bakeoff.md): same cleaning, same baseline model, CV macro-F1 0.756 vs 0.659. TweetEval is then reused as a **domain-shift check**.

**Known limitations:**
- English, US airlines only, one week in February 2015.
- Crowd labels are noisy: 27% of tweets have annotator confidence below 0.7.
- Labels describe sentiment *towards the airline experience*, which is narrower than general brand conversation.
- It is from 2015, so newer slang and platforms are missing.

**How its labels differ from real brand conversations:** Real brand mentions include spam, promotions, mixed or multi-aspect opinions, other languages and code-mixing (e.g. Hinglish), images and replies whose context sits in a thread. A three-label scheme forces mixed posts into one class.

**Timestamps:** the dataset has `tweet_created`, but the dashboard never uses it. All dashboard dates and filters use the time each **prediction** was made, as the brief requires. Nothing is fabricated.

**Data artifact found during EDA:** the published CSV replaced every `late` and `cancel` (and some `book`) substring with complaint-category names, e.g. `chocolate` → `chocoLate Flight`, `cancelled` → `Cancelled Flightled`. The natural words *late* and *cancel* appear **zero times**. `data.py` reverses this before cleaning (1,616 tweets affected). Without the repair the model could not learn the most common airline complaints. See [EDA §2](reports/eda.md).

---

## 5. Preprocessing

`python -m sentiment_ml.pipeline` runs every step end to end (`ml/sentiment_ml/`):

1. **Inspect and validate** (`data.py`): checksum, required columns, missing values, empty texts, invalid labels.
2. **Repair** the dataset's find-and-replace artifacts.
3. **Clean** each tweet with `clean_text` (`preprocessing.py`). This is the same function the API uses, so there is no training/serving skew.
4. **De-duplicate** on the *cleaned* text. Duplicate tweet IDs (155) and conflicting-label copies (153, where annotators labelled identical text differently) are dropped. Remaining duplicates (100) keep one copy. This happens **before** splitting, so an identical input cannot sit in both train and test. Result: 14,640 → 14,232 rows.
5. **Stratified split** 80/20 (`random_state=42`): **11,385 train / 2,847 test**, with identical class proportions. No vectoriser is fitted before this point; TF-IDF lives inside the model pipeline and is re-fitted on every cross-validation fold.
6. **EDA** report with figures: label distribution, text length per class, top tokens per class, sentiment by airline, label quality and cleaning examples ([reports/eda.md](reports/eda.md)).

### Cleaning steps and the signal they could destroy

Each step's effect was **measured** with a cleaning ablation: switch one step off, re-run 5-fold CV ([evaluation §5](reports/evaluation.md#5-cleaning-ablation-which-cleaning-steps-help-or-hurt)).

| Step | Risk to sentiment signal | How it's handled | CV Δ if removed |
|---|---|---|---|
| HTML entities, Unicode NFKC | none | `&amp;` → `&`, fancy fonts → plain letters | – |
| URLs → `<url>` | none, but random URL tokens add noise | placeholder keeps "has a link" | −0.002 |
| @mentions → `<user>` | low; the handle identifies the brand, not the feeling | prevents a brand shortcut ("@united = negative") that would not transfer to other brands | −0.003 |
| Hashtags | **high** if deleted (`#fail`, `#NeverAgain`) | keep the words, drop `#`, split CamelCase | −0.003 |
| Text emoticons `:) :( <3` | **high**; they are punctuation and would be stripped | converted to tokens (`<smile>`, `<sad>`, `<heart>`) before punctuation removal | −0.003 |
| Emojis | **high** if deleted | converted to names (`:face_with_tears_of_joy:`) | −0.002 |
| `!` and `?` | **high**: intensity and questions (neutral) | kept as tokens; repeated `!!!` → `!` | **−0.010** |
| Lowercasing | ALL-CAPS shouting is lost | accepted trade-off | – |
| Elongation `soooo` → `soo` | low | keeps two letters so emphasis is still distinguishable | 0.000 |
| Stop words | **high**: standard lists delete *not, no, never* | **not removed** | – |
| Negation marking (`not neg_good`) | – | tested and **not adopted**: CV −0.002; bigrams like "not good" already capture negation | – |

All steps together vs. minimal cleaning (lowercase + split): **+0.017** CV macro-F1.

---

## 6. Model and evaluation

Full details: **[reports/evaluation.md](reports/evaluation.md)**.

**Selection.** Five candidates were tuned with 5-fold stratified cross-validation **on the training split only** (scoring: macro-F1). The test split was used once, at the end.

| Model | CV macro-F1 | Test macro-F1 | Test accuracy |
|---|---|---|---|
| Dummy (always "negative") | 0.259 ± 0.000 | 0.259 | 0.637 |
| TF-IDF + Complement Naive Bayes | 0.735 ± 0.009 | 0.722 | 0.795 |
| TF-IDF + Linear SVM | 0.755 ± 0.008 | 0.761 | 0.820 |
| **TF-IDF + Logistic Regression (served)** | **0.758 ± 0.009** | **0.754** | **0.809** |
| TF-IDF words + char n-grams + Logistic Regression | 0.761 ± 0.008 | 0.763 | 0.810 |

**Why Logistic Regression is served:** a rule fixed before looking at test results says to serve LogReg unless another model beats it by more than 0.01 CV macro-F1. The char-n-gram variant was only 0.003 ahead, within one standard deviation. LogReg gives real probabilities (FR-02) and exact per-word explanations; Linear SVM has no native probabilities. Served settings: word 1–2-grams, `min_df=1`, `sublinear_tf`, `C=2`, `class_weight="balanced"`.

**Why macro-F1 is the headline:** 64% of tweets are negative. The dummy model scores 0.637 accuracy while being useless (macro-F1 0.259). Macro-F1 weights negative, neutral and positive equally.

**Class imbalance:** balanced class weights beat no weighting in CV (0.758 vs 0.741). This was chosen over resampling: no duplicated or synthetic tweets, and nothing to leak.

**Test results (served model):**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| negative | 0.883 | 0.877 | 0.880 | 1,814 |
| neutral | 0.655 | 0.654 | 0.654 | 592 |
| positive | 0.718 | 0.739 | 0.729 | 441 |
| **macro avg** | **0.752** | **0.757** | **0.754** | 2,847 |

The confusion matrix, calibration plot, label-noise breakdown and domain-shift check are in the evaluation report. Highlights:
- **Confidence is informative but an estimate.** Predictions above 0.9 confidence are right 98% of the time. The 17% below 0.55 are right only 52% of the time (vs 87% for the rest), so they are flagged in the UI.
- **Label noise caps measurable accuracy.** 89% accuracy where annotators fully agreed, about 63% where they did not.
- **Domain shift.** On general tweets (TweetEval) macro-F1 falls to about 0.48.

**Error analysis:** 543 of 2,847 test tweets are misclassified. The 24 most confident mistakes were reviewed by hand and grouped into six patterns: sarcasm and ironic thanks, label noise, mixed or "story arc" tweets, neutral requests that mention problems (the most common error), replies missing their thread context, and slang or quoted text ([evaluation §10](reports/evaluation.md#10-error-analysis)).

**Artifacts:** `artifacts/models/tfidf-logreg-1.0.0/` holds `model.joblib` (the whole pipeline: cleaner → TF-IDF → classifier) and `metadata.json` (version, SHA-256, library versions, hyper-parameters, dataset info, metrics, comparison, top words per class, limitations). The API loads it at startup. It refuses a file whose checksum doesn't match, and a model trained with a different preprocessing version.

---

## 7. API

Interactive docs: http://localhost:8000/docs. All endpoints return JSON.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/predict` | Classify one post |
| POST | `/api/predict/batch` | Classify a CSV file (column `text`, ≤ 500 rows, ≤ 1 MB) |
| GET | `/api/predictions` | Paginated history; filters `sentiment`, `date_from`, `date_to`, `page`, `page_size` |
| GET | `/api/predictions/{id}` | One stored prediction |
| GET | `/api/analytics/summary` | Totals, distribution, time series, cache counts (same filters) |
| GET | `/api/cache/stats` | Live Redis statistics |
| GET | `/api/model` | Model card: version, metrics, comparison, top words, limitations |
| GET | `/health` | API + PostgreSQL + Redis + model status (503 if the model or database is down) |
| GET | `/health/live` | Liveness probe (no dependency checks) |

Changes from the suggested contract (all additive): batch, single-record, cache-stats, model and liveness endpoints. The predict response also carries `probabilities`, `top_words`, `is_low_confidence` and `latency_ms`.

### Examples

```bash
curl -s -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "My flight was cancelled and nobody at the desk helped"}'
```

```json
{
  "id": "29bc8e35-363c-47d2-8d05-0b49493f2775",
  "text": "My flight was cancelled and nobody at the desk helped",
  "sentiment": "negative",
  "confidence": 0.9147,
  "probabilities": {"negative": 0.9147, "neutral": 0.0224, "positive": 0.0629},
  "top_words": [
    {"token": "cancelled", "display": "cancelled", "weight": 0.5882},
    {"token": "and", "display": "and", "weight": 0.2552},
    {"token": "was cancelled", "display": "was cancelled", "weight": 0.2242},
    {"token": "flight was", "display": "flight was", "weight": 0.1941},
    {"token": "my", "display": "my", "weight": 0.1832}
  ],
  "is_low_confidence": false,
  "model_version": "tfidf-logreg@1.0.0+9cb76b11",
  "cache_status": "miss",
  "latency_ms": 11.49,
  "created_at": "2026-10-21T12:54:08.634637Z"
}
```

Send the same request again and `cache_status` becomes `"hit"`. The response header `X-Cache: HIT` and the API log line show the same (latency 11.49 ms → 0.75 ms):

```json
{"timestamp": "2026-10-21T12:54:08.715903+00:00", "level": "INFO", "logger": "app.services.prediction", "message": "Prediction served", "request_id": "decbb66c63284ff5ac35f80282d1e4cf", "event": "prediction", "cache_status": "hit", "model_version": "tfidf-logreg@1.0.0+9cb76b11", "sentiment": "negative", "latency_ms": 0.75, "text_sha256": "2fe4398f3c67"}
```

To see these lines yourself: `docker compose logs -f api`.

```bash
curl -s "http://localhost:8000/api/predictions?sentiment=negative&date_from=2026-10-01T00:00:00Z&page=1&page_size=20"
curl -s "http://localhost:8000/api/analytics/summary?date_from=2026-10-20T00:00:00Z"
curl -s -F "file=@sample.csv" http://localhost:8000/api/predict/batch
curl -s http://localhost:8000/health
```

### Errors: one envelope everywhere

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Text must not be empty.",
    "details": [{"field": "text", "message": "Text must not be empty."}],
    "request_id": "9f1c2b7e4a0d4c55"
  }
}
```

| Case | Status | Code |
|---|---|---|
| Missing/empty/whitespace-only text, wrong type, extra field, malformed JSON | 422 | `VALIDATION_ERROR` |
| Text longer than 1000 characters | 422 | `VALIDATION_ERROR` |
| Text with nothing analysable (e.g. only punctuation) | 422 | `VALIDATION_ERROR` |
| Invalid filters (unknown sentiment, `date_from` after `date_to`, `page_size` > 100) | 422 | `VALIDATION_ERROR` |
| Unknown prediction id | 404 | `NOT_FOUND` |
| Batch file too large / not CSV | 413 / 415 | `PAYLOAD_TOO_LARGE` / `UNSUPPORTED_MEDIA_TYPE` |
| Model not loaded / database unreachable | 503 | `MODEL_UNAVAILABLE` / `DATABASE_UNAVAILABLE` |
| Anything unexpected (logged with a stack trace, never returned) | 500 | `INTERNAL_ERROR` |

Every response carries an `X-Request-ID` header that matches the `request_id` in the logs.

---

## 8. Database design

One table, `predictions`, created by an Alembic migration (`backend/alembic/versions/0001_create_predictions.py`). A test checks that the migration and the ORM model never drift apart.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | generated by the API |
| `text` | TEXT | the submitted post (stripped) |
| `text_sha256` | CHAR(64) | hash of the *normalised* text, used to count unique posts |
| `sentiment` | VARCHAR(16) | CHECK in (`negative`, `neutral`, `positive`) |
| `confidence` | DOUBLE | CHECK 0–1 |
| `prob_negative`, `prob_neutral`, `prob_positive` | DOUBLE | full probability distribution |
| `top_words` | JSONB | explanation shown in the UI |
| `model_version` | VARCHAR(64) | e.g. `tfidf-logreg@1.0.0+9cb76b11` |
| `cache_status` | VARCHAR(8) | CHECK in (`hit`, `miss`, `bypass`) |
| `source` | VARCHAR(8) | CHECK in (`single`, `batch`) |
| `batch_id` | UUID NULL | groups rows from one CSV upload |
| `latency_ms` | DOUBLE | server-side processing time |
| `created_at` | TIMESTAMPTZ | prediction time (UTC); used by every date filter |

**Indexes:**
- `(created_at DESC)` for newest-first history and date ranges.
- `(sentiment, created_at DESC)` for the sentiment + date-range filter.
- `(model_version)` and `(batch_id)`.

**Design choices:**
- The table is an **event log**: every request is stored, including cache hits. Dashboard volumes and the cache hit rate therefore come from stored data.
- All queries go through SQLAlchemy expressions, so they are parameterised and never built from raw input.
- Aggregations (counts, averages, `date_trunc` time buckets) run inside PostgreSQL.

---

## 9. Cache strategy

| Aspect | Choice |
|---|---|
| Key | `sentiment:v1:{model_version}:{sha256(normalised text)}` |
| Value | JSON: sentiment, confidence, probabilities, top words |
| TTL | `CACHE_TTL_SECONDS`, default 86,400 (1 day) |
| Eviction | Redis `maxmemory 128mb` + `allkeys-lru` (a pure cache, no disk persistence) |
| Failures | never cached: the value is written only after the model returns successfully |
| Redis down | prediction still succeeds with `cache_status: "bypass"`; warning logged; `/health` = `degraded`. A circuit breaker then skips Redis for 30 s, so only one request pays the connection timeout |
| Observability | `cache_status` in the response, `X-Cache` header, one log line per prediction, stored per row, dashboard panel + `/api/cache/stats` |

**Why the normalised text?** The key contains exactly what determines the answer: the model version and the text *as the model sees it*. Posts that differ only in case, spacing, repeated punctuation or which brand they @mention share one entry, and a hit can never return a different answer than the model would. The SHA-256 keeps keys short and keeps raw user text out of key names.

**What happens when the model is retrained?** The model version includes the first 8 characters of the model file's SHA-256 (`…+9cb76b11`). A retrained model is a different file, so it gets a different version, even if nobody bumps `1.0.0`. Every key changes, the old entries are simply never read again, and they expire through the TTL. A change to the cleaning code bumps `PREPROCESSING_VERSION`, and the API refuses to serve a model trained with a different one, which forces a retrain and therefore new keys.

---

## 10. Frontend

Next.js (App Router, TypeScript), Tailwind CSS + shadcn/ui, Recharts, TanStack Query. Five pages:

- **Analyze:** post input with character counter, example posts, result card with the label, *estimated* confidence, all three probabilities, a low-confidence callout, **cache HIT/MISS badge with latency**, model version, and "Why this label?" with the contributing words highlighted in the text. "Analyze again" demonstrates a cache hit in one click.
- **Dashboard:** filter bar (sentiment, date range, quick ranges; synced to the URL), KPI cards, sentiment donut, sentiment-over-time chart, cache panel (stored hit/miss + live Redis stats) and a recent-predictions table. Everything is computed from stored predictions.
- **History:** filterable, paginated table with a detail drawer and CSV export.
- **Batch:** CSV upload with preview and validation, per-row results, summary chart and download.
- **Model:** model card with headline metrics, per-class table, confusion-matrix heatmap, model comparison, the words the model associates with each sentiment, and limitations.

Every data view has loading skeletons, empty states and error states with a retry button. Sentiment is always shown with colour **and** icon **and** text (colour-blind safe). Dark mode is supported, and the system-status pill polls `/health`.

---

## 11. Configuration

All configuration comes from environment variables. [`.env.example`](.env.example) documents every value, and the API's settings live in `backend/app/config.py`. No secrets are committed: `.env` is git-ignored, and the compose defaults are for local use only.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `…@localhost:5432/sentiment` (compose sets `…@db:5432/…`) | SQLAlchemy URL (`postgres://` URLs from hosting providers are normalised) |
| `REDIS_URL` | `redis://localhost:6379/0` (compose sets `redis://redis:6379/0`) | cache |
| `MODEL_DIR` | `artifacts/models/tfidf-logreg-1.0.0` | model artifact to load |
| `CACHE_ENABLED` / `CACHE_TTL_SECONDS` | `true` / `86400` | cache switch and lifetime |
| `MAX_TEXT_LENGTH` | `1000` | input limit (characters) |
| `BATCH_MAX_ROWS` / `BATCH_MAX_BYTES` | `500` / `1000000` | CSV limits |
| `LOW_CONFIDENCE_THRESHOLD` | `0.55` | below this the UI flags a prediction |
| `LOG_LEVEL` | `INFO` | JSON logs to stdout |
| `CORS_ORIGINS` | `http://localhost:3000` | only needed if a browser calls the API directly |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `sentiment` / `sentiment` (local only) / `sentiment` | compose database. The password is applied only when the volume is first created; after changing it, run `docker compose down -v` |
| `API_INTERNAL_URL` (frontend, build time) | `http://api:8000` | where Next.js forwards `/api` |

---

## 12. Testing and CI

| Suite | Command | Covers |
|---|---|---|
| ML (28 tests) | `pytest ml/tests` | every cleaning rule (negations kept, emoticons, emojis, idempotence), artifact repair, de-duplication and conflicting labels, stratified leakage-free deterministic split, model save/load, checksum and preprocessing-version guards, explanations |
| API (85 tests) | `cd backend && pytest` | prediction responses; every validation error and its envelope; **cache-hit path** (miss → hit, normalised variants hit, new model version misses, failures not cached, Redis down → bypass, circuit breaker pauses Redis calls); history filters and pagination; analytics; batch; health states; migration ↔ ORM consistency |
| Frontend (22 tests) | `cd frontend && npm test` | sentiment and cache badges, form validation, error-envelope parsing, word highlighting |

API tests run against a real PostgreSQL (with the Alembic migration applied), fakeredis and a small fixture model. Start a test database with `docker run -d -p 5433:5432 -e POSTGRES_USER=sentiment -e POSTGRES_PASSWORD=sentiment -e POSTGRES_DB=sentiment_test postgres:16-alpine`.

**CI** ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every push:
- ML tests
- API tests against a PostgreSQL service container
- frontend lint, type-check, tests and production build
- a full `docker compose build`

---

## 13. Deployment

**Local:** `docker compose up --build` (above).

**Hosted demo: https://sentiment-pulse-tawny.vercel.app.** The frontend runs on **Vercel**. The API, PostgreSQL and Key Value (Redis-compatible) run on **Render** ([render.yaml](render.yaml), Singapore region) at https://sentiment-pulse-api-f18c.onrender.com (API docs at [`/docs`](https://sentiment-pulse-api-f18c.onrender.com/docs)).
1. **Render:** New → Blueprint → select this repository. This creates the API (built from `backend/Dockerfile`), a PostgreSQL database and a Key Value instance, and wires `DATABASE_URL` and `REDIS_URL`. Migrations run on start.
2. **Vercel:** project root directory `frontend`, with `API_INTERNAL_URL` set to the Render API's URL (shown on the service page; here `https://sentiment-pulse-api-f18c.onrender.com`). Next.js forwards `/api` and `/health` to it, so no CORS setup is needed. Deployed with `cd frontend && vercel deploy --prod`.

Free-tier notes:
- Render free web services sleep after about 15 minutes idle, and waking takes up to a minute. Two mitigations:
  - A scheduled GitHub Actions workflow ([keep-warm.yml](.github/workflows/keep-warm.yml)) pings `/health/live` every 10 minutes.
  - If the API is still asleep, the frontend keeps retrying with back-off for about a minute instead of failing, and the status pill shows "Waking up the API…".
- Render's free PostgreSQL expires after 30 days.
- The hosted demo is public, so it must not be used for sensitive text.

---

## 14. Design decisions and trade-offs

- **A simple, explainable model over a complex one.** TF-IDF + Logistic Regression trains in seconds on a CPU, gives probabilities and exact per-word explanations, and was within noise of the best candidate. Pretrained models were excluded by the brief.
- **Decisions are made on cross-validation, and the test set is used once.** The selection tolerance was written down before the test evaluation.
- **Cleaning was measured, not assumed.** The ablation shows each step's effect. Negation marking was tested and rejected.
- **The data repair stays in the data layer.** Dataset-specific fixes live in `data.py`; the shared `clean_text` contains only rules that are valid for live posts.
- **One preprocessing function for training and serving** (`sentiment_ml` package installed into the API image). The version is checked when the model loads.
- **The model version includes the artifact hash.** This makes cache invalidation automatic and auditable.
- **Every request is stored.** This trades table size for honest analytics (volume, hit rate, model versions over time).
- **The cache is optional.** Redis failures degrade to `bypass` instead of failing requests. Timeouts are short (1 s) and there are no retries.
- **Sync FastAPI + SQLAlchemy.** Inference is CPU-bound, so async adds complexity without benefit here. FastAPI runs sync endpoints in a thread pool.
- **Same-origin proxy.** Next.js forwards `/api` to the API, so the browser never makes cross-origin calls.
- **Non-root containers, health-checked startup order, migrations on start.** `docker compose up` works from a clean clone with no manual steps.

---

## 15. Known limitations

- **Domain:** trained on English tweets to six US airlines from February 2015. Macro-F1 drops to about 0.48 on general tweets, so the model needs re-training or at least re-evaluation for other brands, industries, languages or code-mixed text.
- **Understanding:** a bag-of-words model adds up word weights. It does not understand sarcasm ("thanks for the robotic assistance" → positive), irony, long-range negation, or posts that complain and then praise.
- **Mixed sentiment** is forced into one label; there is no *mixed* class or aspect-level sentiment.
- **Label noise:** about a quarter of the labels have annotator confidence below 1.0, which caps measurable accuracy (89% on full-agreement tweets vs about 63% on low-agreement ones).
- **Neutral** is the hardest class (F1 0.65): questions, information and mild opinions overlap.
- **Confidence** is an estimate. Balanced class weights shift probabilities towards the minority classes.
- **Analytics** count prediction events (including repeated posts); `unique_texts` gives the de-duplicated count.
- **Explanations** describe what the *model* used, not ground truth. Bigrams can appear as explanations, and stop words sometimes carry weight.
- **Platform:** there is no authentication or rate limiting (out of scope), and the batch size limit is enforced after upload rather than at a proxy.

---

## 16. Scaling, monitoring and drift

**To millions of posts per day**, in roughly this order:
1. **Decouple ingestion from inference.** Put posts on a queue (Kafka, SQS or Redis Streams). Stateless workers predict in micro-batches (`predict_many` is already vectorised) and write results with bulk inserts.
2. **Scale horizontally.** The model file is about 3 MB and CPU-only, so many API or worker replicas can run behind a load balancer. Each loads the artifact at startup. Database migrations, which today run in each container's entrypoint, would move to a single release step so that replicas don't race.
3. **Database.** Partition `predictions` by month on `created_at`. Serve dashboard numbers from pre-aggregated rollup tables or materialised views, refreshed incrementally, instead of scanning raw rows. Use keyset pagination instead of `OFFSET`. Add read replicas for analytics.
4. **Cache.** Use a managed Redis cluster, cache analytics responses for short TTLs, and keep the versioned keys.
5. **Model registry** (e.g. MLflow) instead of committed artifacts, plus a canary or shadow rollout for new versions.

**Detecting drift** (the model getting worse on new data):
- **Input drift:** track the share of tokens the model has never seen (out-of-vocabulary rate), text length, emoji and language mix, and compare their distributions to the training data (PSI or KS tests).
- **Prediction drift:** watch the daily class distribution and the confidence distribution. A falling average confidence or a rising low-confidence share is an early warning, and both are already visible on the dashboard.
- **Ground truth:** routinely label a small random sample (plus low-confidence posts), track macro-F1 over time, and retrain when it drops below a threshold. The pipeline is one command and deterministic.

**With one more week:**
- use annotator agreement as sample weights
- evaluate a *mixed* class
- add conversation context
- calibrate probabilities on a held-out fold
- add OOV-rate and confidence-drift charts
- add rate limiting and auth for the hosted demo
- add Playwright end-to-end tests

---

## 17. Project structure

```
sentiment-pulse/
├── ml/sentiment_ml/        # data, preprocessing (shared with the API), eda, experiments, evaluate,
│                           # error_analysis, explain, artifacts, inference, pipeline
├── ml/tests/
├── data/raw/               # Tweets.csv (+ licence/attribution); data/processed/ is generated
├── artifacts/models/       # tfidf-logreg-1.0.0/{model.joblib, metadata.json}
├── reports/                # eda.md, evaluation.md, dataset_bakeoff.md, figures/
├── backend/                # FastAPI app (api/, schemas/, services/, db/, core/), Alembic, tests, Dockerfile
├── frontend/               # Next.js app, components, lib/api.ts, tests, Dockerfile
├── scripts/dataset_bakeoff.py
├── docker-compose.yml      # + docker-compose.dev.yml (publishes db/redis ports for local dev)
├── render.yaml             # Render blueprint (API + PostgreSQL + Key Value)
└── .github/workflows/ci.yml
```

---

## 18. Use of AI coding assistants

I used **Claude Code (Anthropic)** as a pair programmer throughout:
- to plan the architecture against the brief's rubric
- to scaffold and write code for the ML pipeline, backend and frontend, plus tests and Docker/CI configuration
- to draft this README and the reports
- to research dataset licences
- to script the demo video's screen recording (a Playwright script drives the app in Chrome); the narration is mine

Commits made with its help carry a `Co-Authored-By` trailer.

I made the key decisions myself and verified the results:
- dataset choice via the bake-off
- the model selection rule
- macro-F1 as the headline metric
- cache key design and graceful degradation
- the frontend framework

I reviewed the code, and I can explain and modify every part of it. All metrics in this repository were produced by running the code, not written by hand.
