"use client";

import { FilterX } from "lucide-react";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useFilters } from "@/hooks/use-filters";
import {
  dateRangeError,
  EMPTY_FILTERS,
  hasActiveFilters,
  QUICK_RANGES,
  type QuickRange,
} from "@/lib/filters";
import { isSentiment, SENTIMENT_STYLES, SENTIMENTS } from "@/lib/sentiment";

/** Sentiment + date filters shared by Dashboard and History, synced to the URL. */
export function FilterBar({ isRefreshing = false }: { isRefreshing?: boolean }) {
  const id = useId();
  const { filters, setFilters } = useFilters();
  const rangeError = dateRangeError(filters);
  const hasCustomDates = Boolean(filters.from || filters.to);
  const quickValue = filters.range ?? (hasCustomDates ? "" : "all");

  function setQuickRange(value: string) {
    if (!value) return; // clicking the active item would otherwise clear the group
    setFilters({
      ...filters,
      range: value === "all" ? null : (value as QuickRange),
      from: null,
      to: null,
    });
  }

  return (
    // Sticky only from tablet width up: on a phone the stacked filters would cover the screen.
    <div className="-mx-4 border-b bg-background/85 px-4 py-3 backdrop-blur-md md:sticky md:top-14 md:z-20 md:-mx-8 md:px-8">
      <div role="group" aria-label="Filters" className="grid items-end gap-3 sm:flex sm:flex-wrap">
        <Field label="Sentiment" htmlFor={`${id}-sentiment`}>
          <Select
            value={filters.sentiment ?? "all"}
            onValueChange={(value) =>
              setFilters({ ...filters, sentiment: isSentiment(value) ? value : null })
            }
          >
            <SelectTrigger id={`${id}-sentiment`} className="w-full sm:w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sentiments</SelectItem>
              {SENTIMENTS.map((sentiment) => {
                const { label, icon: Icon, textClass } = SENTIMENT_STYLES[sentiment];
                return (
                  <SelectItem key={sentiment} value={sentiment}>
                    <Icon className={textClass} />
                    {label}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </Field>

        <Field label="From" htmlFor={`${id}-from`}>
          <Input
            id={`${id}-from`}
            type="datetime-local"
            value={filters.from ?? ""}
            max={filters.to ?? undefined}
            aria-invalid={Boolean(rangeError)}
            onChange={(event) =>
              setFilters({ ...filters, range: null, from: event.target.value || null })
            }
            className="w-full sm:w-52"
          />
        </Field>

        <Field label="To" htmlFor={`${id}-to`}>
          <Input
            id={`${id}-to`}
            type="datetime-local"
            value={filters.to ?? ""}
            min={filters.from ?? undefined}
            aria-invalid={Boolean(rangeError)}
            onChange={(event) =>
              setFilters({ ...filters, range: null, to: event.target.value || null })
            }
            className="w-full sm:w-52"
          />
        </Field>

        <div className="flex items-end gap-2">
          <ToggleGroup
            type="single"
            variant="outline"
            spacing={0}
            value={quickValue}
            onValueChange={setQuickRange}
            aria-label="Quick date range"
          >
            {QUICK_RANGES.map((range) => (
              <ToggleGroupItem
                key={range.value}
                value={range.value}
                aria-label={`Last ${range.label}`}
              >
                {range.label}
              </ToggleGroupItem>
            ))}
            <ToggleGroupItem value="all">All time</ToggleGroupItem>
          </ToggleGroup>

          <Button
            variant="ghost"
            onClick={() => setFilters(EMPTY_FILTERS)}
            disabled={!hasActiveFilters(filters)}
          >
            <FilterX />
            Reset
          </Button>
        </div>

        {isRefreshing && (
          <span className="hidden items-center gap-1.5 self-center text-xs text-muted-foreground sm:ml-auto sm:flex">
            <Spinner className="size-3.5" />
            Updating
          </span>
        )}
      </div>

      {rangeError && (
        <p role="alert" className="mt-2 text-xs text-destructive">
          {rangeError}
        </p>
      )}
    </div>
  );
}

/** A control with its label stacked above it. */
function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-medium text-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}
