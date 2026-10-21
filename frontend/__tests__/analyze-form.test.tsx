import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AnalyzeView } from "@/components/analyze/analyze-view";
import { TooltipProvider } from "@/components/ui/tooltip";
import { predict } from "@/lib/api";
import type { PredictResponse } from "@/lib/types";

// Keep the real ApiError class; replace only the network call.
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  predict: vi.fn(),
}));

const RESULT: PredictResponse = {
  id: "pred_1",
  text: "Great flight!",
  sentiment: "positive",
  confidence: 0.91,
  probabilities: { positive: 0.91, neutral: 0.06, negative: 0.03 },
  top_words: [{ token: "great", display: "great", weight: 0.84 }],
  is_low_confidence: false,
  model_version: "sentiment-logreg@1.0.0+abcd1234",
  cache_status: "miss",
  latency_ms: 14.3,
  created_at: new Date().toISOString(),
};

function renderAnalyze() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>
        <AnalyzeView />
      </TooltipProvider>
    </QueryClientProvider>,
  );
}

const analyzeButton = () => screen.getByRole("button", { name: "Analyze" });
const textBox = () => screen.getByLabelText("Post text");

describe("Analyze form", () => {
  beforeEach(() => {
    vi.mocked(predict).mockReset();
  });

  it("disables the Analyze button while the text is empty", () => {
    renderAnalyze();
    expect(analyzeButton()).toBeDisabled();

    fireEvent.change(textBox(), { target: { value: "   " } });
    expect(analyzeButton()).toBeDisabled();
  });

  it("shows an inline error and blocks submitting over 1000 characters", () => {
    renderAnalyze();
    fireEvent.change(textBox(), { target: { value: "a".repeat(1001) } });

    expect(screen.getByText("Too long by 1 character. The limit is 1,000.")).toBeInTheDocument();
    expect(textBox()).toHaveAttribute("aria-invalid", "true");
    expect(analyzeButton()).toBeDisabled();
  });

  it("sends the trimmed text to the API and shows the result", async () => {
    vi.mocked(predict).mockResolvedValue(RESULT);
    const user = userEvent.setup();
    renderAnalyze();

    await user.type(textBox(), "   Great flight!  ");
    await user.click(analyzeButton());

    expect(predict).toHaveBeenCalledTimes(1);
    expect(predict).toHaveBeenCalledWith("Great flight!");
    expect(await screen.findByText("Cache MISS · computed by model · 14.3 ms")).toBeInTheDocument();
  });
});
