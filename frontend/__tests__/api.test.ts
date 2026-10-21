import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getHealth, parseApiError, predict } from "@/lib/api";

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("parseApiError", () => {
  it("reads code, message, field details and request id from the error envelope", async () => {
    const error = await parseApiError(
      jsonResponse(
        {
          error: {
            code: "VALIDATION_ERROR",
            message: "The request is invalid.",
            details: [{ field: "text", message: "Text must be at most 1000 characters." }],
            request_id: "req_123",
          },
        },
        422,
      ),
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "The request is invalid.",
      requestId: "req_123",
    });
    expect(error.fieldMessage("text")).toBe("Text must be at most 1000 characters.");
    expect(error.fieldMessage("file")).toBeUndefined();
  });

  it("treats a 5xx without an envelope as the API being unreachable", async () => {
    const error = await parseApiError(new Response("Internal Server Error", { status: 500 }));

    expect(error).toMatchObject({
      status: 500,
      code: "API_UNREACHABLE",
      requestId: null,
      details: [],
    });
    expect(error.message).toContain("HTTP 500");
  });
});

describe("API client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("throws an ApiError for non-2xx responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: "MODEL_UNAVAILABLE",
            message: "Model not loaded.",
            details: [],
            request_id: "req_9",
          },
        },
        503,
      ),
    );

    await expect(predict("hello")).rejects.toMatchObject({
      code: "MODEL_UNAVAILABLE",
      status: 503,
    });
  });

  it("reports a failed connection as a NETWORK_ERROR", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(predict("hello")).rejects.toMatchObject({ code: "NETWORK_ERROR", status: 0 });
  });

  it("treats a 503 health report as data, not an error", async () => {
    const report = {
      status: "down",
      version: "1.0.0",
      environment: "test",
      uptime_seconds: 5,
      checks: {
        model: { status: "ok", version: "m@1.0.0+abc" },
        database: { status: "down", latency_ms: null, error: "connection refused" },
        redis: { status: "ok", latency_ms: 0.4, error: null },
      },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(report, 503));

    await expect(getHealth()).resolves.toEqual(report);
  });
});
