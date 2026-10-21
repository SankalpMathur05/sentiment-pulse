import type {
  AnalyticsParams,
  AnalyticsSummary,
  ApiErrorDetail,
  ApiErrorEnvelope,
  BatchResponse,
  CacheStats,
  HealthReport,
  ModelInfo,
  PaginatedPredictions,
  PredictionListParams,
  PredictionRecord,
  PredictResponse,
} from "./types";

// All paths are same-origin: next.config.ts proxies /api/* and /health to the backend.

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ApiErrorDetail[];
  readonly requestId: string | null;

  constructor(init: {
    status: number;
    code: string;
    message: string;
    details?: ApiErrorDetail[];
    requestId?: string | null;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.details = init.details ?? [];
    this.requestId = init.requestId ?? null;
  }

  /** The API's message for one request field (e.g. "text"), if it flagged one. */
  fieldMessage(field: string): string | undefined {
    return this.details.find((detail) => detail.field === field)?.message;
  }
}

function isErrorEnvelope(body: unknown): body is ApiErrorEnvelope {
  if (typeof body !== "object" || body === null || !("error" in body)) return false;
  const error = (body as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

/** For responses without the error envelope, which the API itself always sends. */
function fallbackError(status: number): { code: string; message: string } {
  if (status >= 500 || status === 404) {
    // Most likely the Next.js proxy couldn't reach the backend at all (a 404 without our
    // envelope comes from the hosting platform, e.g. a backend that isn't deployed).
    return {
      code: "API_UNREACHABLE",
      message: `The server didn't get an answer from the API (HTTP ${status}). It may be starting up or offline.`,
    };
  }
  return { code: "HTTP_ERROR", message: `The request failed (HTTP ${status}).` };
}

/** Turn any non-2xx response into an ApiError, using the error envelope when present. */
export async function parseApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Not JSON: e.g. the proxy's own error page when the backend is down.
  }

  if (isErrorEnvelope(body)) {
    const { code, message, details, request_id } = body.error;
    return new ApiError({
      status: response.status,
      code,
      message,
      details: Array.isArray(details) ? details : [],
      requestId: request_id ?? null,
    });
  }

  return new ApiError({
    status: response.status,
    ...fallbackError(response.status),
    requestId: response.headers.get("x-request-id"),
  });
}

/** fetch() that reports "could not connect" as an ApiError instead of a bare TypeError. */
async function send(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(path, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch (error) {
    // Let React Query see its own cancellations as aborts, not failures.
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError({
      status: 0,
      code: "NETWORK_ERROR",
      message: "Couldn't connect to the server. Check your internet connection and try again.",
    });
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await send(path, init);
  if (!response.ok) throw await parseApiError(response);
  return (await response.json()) as T;
}

function withQuery(path: string, params: object): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

// ---- Endpoints -----------------------------------------------------------------

export function predict(text: string): Promise<PredictResponse> {
  return request("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export function predictBatch(file: File): Promise<BatchResponse> {
  const body = new FormData();
  body.append("file", file);
  // No Content-Type header: the browser sets the multipart boundary itself.
  return request("/api/predict/batch", { method: "POST", body });
}

export function getPredictions(
  params: PredictionListParams,
  signal?: AbortSignal,
): Promise<PaginatedPredictions> {
  return request(withQuery("/api/predictions", params), { signal });
}

export function getPrediction(id: string, signal?: AbortSignal): Promise<PredictionRecord> {
  return request(`/api/predictions/${encodeURIComponent(id)}`, { signal });
}

export function getAnalyticsSummary(
  params: AnalyticsParams,
  signal?: AbortSignal,
): Promise<AnalyticsSummary> {
  return request(withQuery("/api/analytics/summary", params), { signal });
}

export function getCacheStats(signal?: AbortSignal): Promise<CacheStats> {
  return request("/api/cache/stats", { signal });
}

export function getModelInfo(signal?: AbortSignal): Promise<ModelInfo> {
  return request("/api/model", { signal });
}

export async function getHealth(signal?: AbortSignal): Promise<HealthReport> {
  const response = await send("/health", { signal });
  // A down API still answers with its health report (HTTP 503; degraded is a 200).
  // That report is data to display, not a failed request.
  if (response.ok || response.status === 503) {
    const body: unknown = await response
      .clone()
      .json()
      .catch(() => null);
    if (typeof body === "object" && body !== null && "status" in body && "checks" in body) {
      return body as HealthReport;
    }
  }
  throw await parseApiError(response);
}
