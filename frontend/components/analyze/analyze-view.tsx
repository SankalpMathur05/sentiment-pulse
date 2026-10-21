"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { PageContainer, PageIntro } from "@/components/layout/page";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, predict } from "@/lib/api";
import { describeError } from "@/lib/errors";
import { PREDICTION_DEPENDENT_KEYS } from "@/lib/queries";
import type { PredictResponse } from "@/lib/types";
import { AnalyzeForm } from "./analyze-form";
import { PredictionResult } from "./prediction-result";
import { SessionHistory } from "./session-history";

const SESSION_SIZE = 5;

export function AnalyzeView() {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [session, setSession] = useState<PredictResponse[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (value: string) => predict(value),
    onSuccess: (result) => {
      setSession((previous) =>
        [result, ...previous.filter((item) => item.id !== result.id)].slice(0, SESSION_SIZE),
      );
      setActiveId(result.id);
      // The new prediction is stored, so the dashboard and history are now out of date.
      for (const queryKey of PREDICTION_DEPENDENT_KEYS) {
        void queryClient.invalidateQueries({ queryKey });
      }
    },
    onError: (error) => {
      const { title, message, requestId } = describeError(error);
      toast.error(title, {
        description: requestId ? `${message} Request ID: ${requestId}` : message,
      });
    },
  });

  const result = session.find((item) => item.id === activeId) ?? null;
  const serverError =
    mutation.error instanceof ApiError ? mutation.error.fieldMessage("text") : undefined;

  function handleTextChange(next: string) {
    setText(next);
    if (mutation.isError) mutation.reset();
  }

  function showFromSession(id: string) {
    setActiveId(id);
    mutation.reset();
  }

  return (
    <PageContainer>
      <PageIntro>
        Paste a social media post to see its sentiment, how sure the model is, and which words drove
        the decision.
      </PageIntro>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_19rem]">
        <div className="grid min-w-0 gap-6">
          <AnalyzeForm
            text={text}
            onTextChange={handleTextChange}
            onAnalyze={(value) => mutation.mutate(value)}
            isPending={mutation.isPending}
            serverError={serverError}
          />
          <PredictionResult
            result={result}
            isPending={mutation.isPending}
            // A field error is already shown under the text box; anything else shows here.
            error={serverError ? null : mutation.error}
            onRetry={() => mutation.variables && mutation.mutate(mutation.variables)}
            onAnalyzeAgain={(value) => mutation.mutate(value)}
          />
        </div>

        <aside className="grid gap-6 lg:sticky lg:top-20">
          <SessionHistory items={session} activeId={activeId} onSelect={showFromSession} />
          <HowItWorks />
        </aside>
      </div>
    </PageContainer>
  );
}

function HowItWorks() {
  const steps = [
    "Your text is cleaned the same way as the training data: links, @mentions and emoji become tokens.",
    "A TF-IDF + Logistic Regression model scores it against positive, neutral and negative.",
    "The result is stored and cached in Redis, so analyzing the same text again is near-instant.",
  ];
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>How it works</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="grid gap-3 text-sm text-muted-foreground">
          {steps.map((step, i) => (
            <li key={step} className="flex gap-2.5">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-[11px] font-medium text-foreground">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
