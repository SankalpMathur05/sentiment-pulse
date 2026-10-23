import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api";
import { shouldRetry, WAKE_UP_RETRIES } from "@/lib/queries";

const unreachable = new ApiError({ status: 504, code: "API_UNREACHABLE", message: "waking up" });
const offline = new ApiError({ status: 0, code: "NETWORK_ERROR", message: "offline" });
const serverError = new ApiError({ status: 500, code: "INTERNAL_ERROR", message: "boom" });
const badInput = new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "empty" });

describe("shouldRetry", () => {
  it("keeps retrying while the API is unreachable (e.g. waking up), up to the limit", () => {
    for (const error of [unreachable, offline]) {
      expect(shouldRetry(0, error)).toBe(true);
      expect(shouldRetry(WAKE_UP_RETRIES - 1, error)).toBe(true);
      expect(shouldRetry(WAKE_UP_RETRIES, error)).toBe(false);
    }
  });

  it("retries other server errors once", () => {
    expect(shouldRetry(0, serverError)).toBe(true);
    expect(shouldRetry(1, serverError)).toBe(false);
  });

  it("never retries a client error, which won't fix itself", () => {
    expect(shouldRetry(0, badInput)).toBe(false);
  });
});
