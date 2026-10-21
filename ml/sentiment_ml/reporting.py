"""Small helpers for writing Markdown reports and figures consistently."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files only; no GUI window needed
import matplotlib.pyplot as plt  # noqa: E402

from . import config  # noqa: E402

SENTIMENT_COLORS = {"negative": "#e11d48", "neutral": "#64748b", "positive": "#10b981"}


def md_table(headers: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def save_figure(fig, name: str) -> str:
    """Save a figure under reports/figures and return its path relative to reports/."""
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES_DIR / name, dpi=130, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    return f"figures/{name}"


def pct(value: float) -> str:
    return f"{value:.1%}"
