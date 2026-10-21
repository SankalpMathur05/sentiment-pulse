import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CacheBadge } from "@/components/sentiment/cache-badge";

describe("CacheBadge", () => {
  it.each([
    ["hit", "HIT"],
    ["miss", "MISS"],
    ["bypass", "BYPASS"],
  ] as const)("compact %s badge reads %s", (status, text) => {
    render(<CacheBadge status={status} compact />);
    expect(screen.getByText(text)).toBeInTheDocument();
  });

  it("spells out a cache hit with its latency", () => {
    render(<CacheBadge status="hit" latencyMs={2.1} />);
    expect(screen.getByText("Cache HIT · 2.1 ms · served from Redis")).toBeInTheDocument();
  });

  it("spells out a cache miss with its latency", () => {
    render(<CacheBadge status="miss" latencyMs={14.3} />);
    expect(screen.getByText("Cache MISS · computed by model · 14.3 ms")).toBeInTheDocument();
  });

  it("explains a bypass when the cache is unavailable", () => {
    render(<CacheBadge status="bypass" latencyMs={9} />);
    expect(screen.getByText("Cache unavailable · computed by model")).toBeInTheDocument();
  });
});
