// TypeScript mirror of the Sentiment Pulse API contract. Field names stay in
// snake_case so responses can be used exactly as they arrive.

export type Sentiment = "negative" | "neutral" | "positive";
export type CacheStatus = "hit" | "miss" | "bypass";
export type PredictionSource = "single" | "batch";

export type SentimentProbabilities = Record<Sentiment, number>;

export interface TopWord {
  token: string;
  display: string;
  weight: number;
}

// ---- Errors ----------------------------------------------------------------

export type ApiErrorCode =
  | "VALIDATION_ERROR"
  | "NOT_FOUND"
  | "PAYLOAD_TOO_LARGE"
  | "UNSUPPORTED_MEDIA_TYPE"
  | "MODEL_UNAVAILABLE"
  | "DATABASE_UNAVAILABLE"
  | "INTERNAL_ERROR";

export interface ApiErrorDetail {
  field: string | null;
  message: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: ApiErrorCode | (string & {});
    message: string;
    details: ApiErrorDetail[];
    request_id: string;
  };
}

// ---- Predictions -------------------------------------------------------------

export interface PredictRequest {
  text: string;
}

export interface PredictResponse {
  id: string;
  text: string;
  sentiment: Sentiment;
  confidence: number;
  probabilities: SentimentProbabilities;
  top_words: TopWord[];
  is_low_confidence: boolean;
  model_version: string;
  cache_status: CacheStatus;
  latency_ms: number;
  created_at: string;
}

export interface PredictionRecord {
  id: string;
  text: string;
  sentiment: Sentiment;
  confidence: number;
  probabilities: SentimentProbabilities;
  top_words: TopWord[];
  is_low_confidence: boolean;
  model_version: string;
  cache_status: CacheStatus;
  source: PredictionSource;
  batch_id: string | null;
  latency_ms: number;
  created_at: string;
}

export interface PaginatedPredictions {
  items: PredictionRecord[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface BatchResultRow {
  row: number;
  text: string;
  sentiment: Sentiment | null;
  confidence: number | null;
  cache_status: CacheStatus | null;
  id: string | null;
  error: string | null;
}

export interface BatchResponse {
  batch_id: string;
  total_rows: number;
  succeeded: number;
  failed: number;
  summary: Record<Sentiment, number>;
  cache: Record<CacheStatus, number>;
  model_version: string;
  results: BatchResultRow[];
}

// ---- Query parameters ----------------------------------------------------------

export interface AnalyticsParams {
  sentiment?: Sentiment;
  date_from?: string;
  date_to?: string;
}

export interface PredictionListParams extends AnalyticsParams {
  page?: number;
  page_size?: number;
}

// ---- Analytics -----------------------------------------------------------------

export interface SentimentShare {
  sentiment: Sentiment;
  count: number;
  percentage: number;
}

export interface TimeseriesBucket {
  bucket: string;
  negative: number;
  neutral: number;
  positive: number;
}

export interface AnalyticsSummary {
  total: number;
  unique_texts: number;
  distribution: SentimentShare[];
  average_confidence: number | null;
  low_confidence_count: number;
  cache: {
    hit: number;
    miss: number;
    bypass: number;
    hit_rate: number | null;
  };
  granularity: "hour" | "day";
  timeseries: TimeseriesBucket[];
  model_versions: { model_version: string; count: number }[];
}

export interface CacheStats {
  enabled: boolean;
  available: boolean;
  ttl_seconds: number;
  keys: number | null;
  hits: number | null;
  misses: number | null;
  hit_rate: number | null;
  used_memory_human: string | null;
}

// ---- Model card ----------------------------------------------------------------

export interface ClassMetrics {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface ModelComparisonRow {
  model: string;
  cv_macro_f1: number;
  cv_macro_f1_std: number;
  test_macro_f1: number;
  test_accuracy: number;
  selected: boolean;
}

export interface ModelInfo {
  name: string;
  version: string;
  semver: string;
  trained_at: string;
  sklearn_version: string;
  preprocessing_version: string;
  labels: string[];
  low_confidence_threshold: number;
  dataset: {
    name: string;
    homepage: string;
    licence: string;
    rows_train: number;
    rows_test: number;
  };
  metrics: {
    accuracy: number;
    macro_precision: number;
    macro_recall: number;
    macro_f1: number;
    weighted_f1: number;
    per_class: Record<string, ClassMetrics>;
    confusion_matrix: number[][];
    confusion_labels: string[];
    log_loss: number;
    brier_score: number;
  };
  comparison: ModelComparisonRow[];
  top_features: Record<string, TopWord[]>;
  limitations: string[];
}

// ---- Health --------------------------------------------------------------------

export type HealthStatus = "ok" | "degraded" | "down";

export interface HealthReport {
  status: HealthStatus;
  version: string;
  environment: string;
  uptime_seconds: number;
  checks: {
    model: { status: string; version: string | null };
    database: { status: string; latency_ms: number | null; error: string | null };
    redis: {
      status: "ok" | "down" | "disabled";
      latency_ms: number | null;
      error: string | null;
    };
  };
}
