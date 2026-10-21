import { ApiError } from "./api";

const TITLES: Record<string, string> = {
  VALIDATION_ERROR: "Some input needs fixing",
  NOT_FOUND: "Not found",
  PAYLOAD_TOO_LARGE: "That file is too large",
  UNSUPPORTED_MEDIA_TYPE: "Unsupported file type",
  MODEL_UNAVAILABLE: "The model isn't available right now",
  DATABASE_UNAVAILABLE: "The database isn't available right now",
  INTERNAL_ERROR: "Something went wrong on the server",
  // Client-side codes (see lib/api.ts) for failures that never reached the API.
  NETWORK_ERROR: "You appear to be offline",
  API_UNREACHABLE: "Can't reach the API",
  HTTP_ERROR: "The request failed",
};

export interface ErrorDescription {
  title: string;
  message: string;
  requestId: string | null;
}

/** A friendly title + message for any error thrown while talking to the API. */
export function describeError(error: unknown): ErrorDescription {
  if (error instanceof ApiError) {
    return {
      title: TITLES[error.code] ?? "Request failed",
      message: error.message,
      requestId: error.requestId,
    };
  }
  return {
    title: "Something went wrong",
    message: error instanceof Error ? error.message : "An unexpected error occurred.",
    requestId: null,
  };
}
