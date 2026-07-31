"""Mandala AI bridge — read brand context and generated content from mandala-bot.

mandala-bot already does the hard part: it talks to Mandala AI Studio and writes
its results to disk (`context.txt` for the brand brief, `output/<run>/…` for
generated content). This module reads those artifacts so the Streamlit app can
ground its own generation in real brand data.

Deliberately read-only. mandala-bot's own README warns that calling Mandala's
internal API with a session cookie risks the account, so triggering live runs
stays a manual step the owner performs in mandala-bot itself.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MANDALA_DIRS = [
    Path(r"D:\LEMED\mandala-bot"),
    Path(__file__).parent.parent / "mandala-bot",
    Path(__file__).parent / "mandala-bot",
]


def find_mandala_dir() -> Path | None:
    """Locate the mandala-bot folder (env var wins, then known locations)."""
    env_dir = os.getenv("MANDALA_BOT_DIR", "").strip()
    candidates = ([Path(env_dir)] if env_dir else []) + DEFAULT_MANDALA_DIRS
    for path in candidates:
        try:
            if path.is_dir():
                return path
        except OSError:
            continue
    return None


def load_brand_context(max_chars: int = 4000) -> str:
    """Read context.txt — the curated brand brief mandala-bot feeds every prompt."""
    base = find_mandala_dir()
    if base is None:
        return ""
    ctx_file = base / "context.txt"
    if not ctx_file.exists():
        return ""
    try:
        text = ctx_file.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("read context.txt failed: %s", e)
        return ""
    # Drop comment-only lines, matching mandala_bot.load_context()
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return "\n".join(lines).strip()[:max_chars]


def list_runs() -> list[Path]:
    """All output run folders, newest first."""
    base = find_mandala_dir()
    if base is None:
        return []
    out = base / "output"
    if not out.is_dir():
        return []
    runs = [p for p in out.iterdir() if p.is_dir()]
    return sorted(runs, key=lambda p: p.name, reverse=True)


def load_run(run_dir: Path) -> list[dict]:
    """Load one run's content_results.json → [{prompt, model, content, images}]."""
    results_file = run_dir / "content_results.json"
    if not results_file.exists():
        return []
    try:
        data = json.loads(results_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("read %s failed: %s", results_file, e)
        return []
    if not isinstance(data, list):
        return []
    items = []
    for row in data:
        if isinstance(row, dict) and (row.get("content") or "").strip():
            items.append({
                "prompt": row.get("prompt", ""),
                "model": row.get("model", ""),
                "content": row.get("content", ""),
                "images": row.get("images") or [],
                "run": run_dir.name,
            })
    return items


def latest_content(limit: int = 5) -> list[dict]:
    """Most recent generated pieces across runs, newest first."""
    items: list[dict] = []
    for run_dir in list_runs():
        items.extend(load_run(run_dir))
        if len(items) >= limit:
            break
    return items[:limit]


def status() -> dict:
    """Summary for the UI: is mandala-bot present, and what does it hold?"""
    base = find_mandala_dir()
    runs = list_runs()
    ctx = load_brand_context()
    return {
        "found": base is not None,
        "path": str(base) if base else "",
        "has_context": bool(ctx),
        "context_chars": len(ctx),
        "runs": len(runs),
        "latest_run": runs[0].name if runs else "",
    }


def build_context_block(include_samples: int = 2, max_chars: int = 3500) -> str:
    """Assemble a prompt-ready context block: brand brief + recent content samples."""
    parts: list[str] = []
    brand = load_brand_context()
    if brand:
        parts.append(f"----- บริบทแบรนด์ (จาก Mandala AI) -----\n{brand}")

    if include_samples > 0:
        samples = latest_content(include_samples)
        if samples:
            joined = "\n\n".join(
                f"[{s['prompt'][:60]}]\n{s['content'][:600]}" for s in samples
            )
            parts.append(f"----- ตัวอย่างคอนเทนต์ที่เคยผลิต -----\n{joined}")

    block = "\n\n".join(parts)
    return block[:max_chars]
