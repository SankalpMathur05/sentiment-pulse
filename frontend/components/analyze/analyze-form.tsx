"use client";

import { Sparkles } from "lucide-react";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Kbd, KbdGroup } from "@/components/ui/kbd";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useIsMac } from "@/hooks/use-is-mac";
import { countChars, formatCount, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import { EXAMPLES } from "./examples";

/** Same limit the API enforces (1–1000 characters after trimming). */
export const MAX_CHARS = 1000;

export function AnalyzeForm({
  text,
  onTextChange,
  onAnalyze,
  isPending,
  serverError,
}: {
  text: string;
  onTextChange: (text: string) => void;
  onAnalyze: (text: string) => void;
  isPending: boolean;
  /** The API's message for the "text" field after a failed request. */
  serverError?: string;
}) {
  const id = useId();
  const isMac = useIsMac();
  const [showEmptyError, setShowEmptyError] = useState(false);

  const trimmed = text.trim();
  const length = countChars(trimmed);
  const tooLong = length > MAX_CHARS;

  let error: string | undefined;
  if (tooLong) {
    const over = length - MAX_CHARS;
    error = `Too long by ${formatCount(over, "character")}. The limit is ${formatNumber(MAX_CHARS)}.`;
  } else if (showEmptyError && length === 0) {
    error = "Enter some text to analyze.";
  } else {
    error = serverError;
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (length === 0) {
      setShowEmptyError(true);
      return;
    }
    if (tooLong || isPending) return;
    onAnalyze(trimmed);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function tryExample(example: string) {
    setShowEmptyError(false);
    onTextChange(example);
    onAnalyze(example);
  }

  return (
    <Card>
      <CardContent>
        <form onSubmit={submit} noValidate className="grid gap-3">
          <label htmlFor={`${id}-text`} className="text-sm font-medium">
            Post text
          </label>
          <Textarea
            id={`${id}-text`}
            value={text}
            onChange={(event) => {
              setShowEmptyError(false);
              onTextChange(event.target.value);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Paste a tweet, review or comment…"
            rows={5}
            aria-invalid={Boolean(error)}
            aria-describedby={`${id}-help ${id}-count`}
            className="min-h-32 resize-y text-[15px] leading-relaxed md:text-[15px]"
          />

          <div className="flex items-start justify-between gap-4 text-xs">
            <p
              id={`${id}-help`}
              className={cn(error ? "text-destructive" : "text-muted-foreground")}
            >
              {error ?? "Up to 1,000 characters. Emoji, @mentions and links are fine."}
            </p>
            <p
              id={`${id}-count`}
              className={cn(
                "shrink-0 font-mono tabular-nums",
                tooLong ? "font-medium text-destructive" : "text-muted-foreground",
              )}
            >
              {formatNumber(length)} / {formatNumber(MAX_CHARS)}
            </p>
          </div>

          <div className="flex flex-col gap-4 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-1 text-xs text-muted-foreground">Try an example</span>
              {EXAMPLES.map((example) => (
                <Button
                  key={example.label}
                  type="button"
                  variant="outline"
                  size="xs"
                  title={example.text}
                  disabled={isPending}
                  onClick={() => tryExample(example.text)}
                  className="rounded-full font-normal"
                >
                  {example.label}
                </Button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              {text && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => onTextChange("")}
                  disabled={isPending}
                >
                  Clear
                </Button>
              )}
              <Button
                type="submit"
                disabled={length === 0 || tooLong || isPending}
                className="min-w-32"
              >
                {isPending ? <Spinner /> : <Sparkles />}
                {isPending ? "Analyzing…" : "Analyze"}
                <KbdGroup className="ml-1 hidden sm:inline-flex" aria-hidden>
                  <Kbd className="bg-primary-foreground/15 text-primary-foreground/80">
                    {isMac ? "⌘" : "Ctrl"}
                  </Kbd>
                  <Kbd className="bg-primary-foreground/15 text-primary-foreground/80">↵</Kbd>
                </KbdGroup>
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
