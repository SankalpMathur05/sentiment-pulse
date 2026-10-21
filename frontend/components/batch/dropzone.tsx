"use client";

import { Upload } from "lucide-react";
import { useId, useState } from "react";
import { BATCH_LIMITS } from "@/lib/csv";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Drag-and-drop area that is also a regular (keyboard-accessible) file picker. */
export function Dropzone({
  onFile,
  disabled = false,
}: {
  onFile: (file: File) => void;
  disabled?: boolean;
}) {
  const id = useId();
  const [dragging, setDragging] = useState(false);

  return (
    <label
      htmlFor={id}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={(event) => {
        // Moving over a child element also fires dragleave; only reset when leaving the zone.
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const file = event.dataTransfer.files[0];
        if (file && !disabled) onFile(file);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border border-dashed px-6 py-12 text-center transition-colors hover:bg-muted/40 has-focus-visible:border-ring has-focus-visible:ring-3 has-focus-visible:ring-ring/50",
        dragging && "border-foreground/40 bg-muted/60",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <span className="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Upload className="size-5" aria-hidden />
      </span>
      <span className="grid gap-1">
        <span className="font-medium">
          {dragging ? "Drop to check the file" : "Drop a CSV here, or "}
          {!dragging && <span className="underline underline-offset-4">browse</span>}
        </span>
        <span className="text-xs text-muted-foreground">
          Needs a <code className="rounded bg-muted px-1 font-mono">text</code> column · up to{" "}
          {BATCH_LIMITS.maxRows} rows · max {formatBytes(BATCH_LIMITS.maxBytes)}
        </span>
      </span>
      <input
        id={id}
        type="file"
        accept=".csv,text/csv"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = ""; // so choosing the same file again still triggers a change
        }}
      />
    </label>
  );
}
