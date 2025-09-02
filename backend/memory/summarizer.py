from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

from openai import OpenAI
from ..config import get_client, model_name

from .manager import list_short_files_due, short_dir


def _client() -> OpenAI | None:
    return get_client()


def _model() -> str:
    return model_name()


def _call_summary(prompt: str, text: str) -> str:
    client = _client()
    if client is None:
        return ""  # Graceful no-op when not configured

    # Use Responses API per requirement
    resp = client.responses.create(model=_model(), input=f"{prompt}\n\n{text}")
    out = ""
    for item in (resp.output or []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    out = part.get("text") or ""
                    break
    return out


def _write_summary(file_path: Path, suffix: str, summary: str) -> Path:
    out_path = file_path.with_suffix(f".summary.{suffix}.md")
    out_path.write_text(summary.strip() + "\n", encoding="utf-8")
    return out_path


def summarize_to_3d(file_path: Path) -> Path:
    text = file_path.read_text(encoding="utf-8")
    prompt = (
        "次の会話ログを要約してください。Markdown の箇条書きで 5 行以内。"
        "固有名詞と好悪のみ強調。"
    )
    summary = _call_summary(prompt, text)
    return _write_summary(file_path, "3d", summary)


def summarize_to_7d(file_path: Path) -> Path:
    text = file_path.read_text(encoding="utf-8")
    prompt = (
        "次の会話ログをさらに圧縮して要約してください。"
        "固有名詞/習慣/好悪のみに限定。Markdown 箇条書き 3 行以内。"
    )
    summary = _call_summary(prompt, text)
    return _write_summary(file_path, "7d", summary)


def purge_14d(file_path: Path) -> None:
    # Remove the original and any summaries
    file_path.unlink(missing_ok=True)
    file_path.with_suffix(".summary.3d.md").unlink(missing_ok=True)
    file_path.with_suffix(".summary.7d.md").unlink(missing_ok=True)


def extract_long_fact(user_and_ai_text: str) -> str:
    """Extract a 1-2 line long-term memory candidate using Responses API."""
    prompt = (
        "次の会話の抜粋から、ユーザー個性/好悪/繰返し言及/喜怒哀楽に関する"
        "重要情報を極小要約で 1-2 行、カテゴリ付与（like/dislike/habit/other）で返してください。"
        "返答は 'category: text' の形式で 1 行のみが望ましい。"
    )
    return _call_summary(prompt, user_and_ai_text)


def daily_maintain() -> dict:
    """Scan short-term files and perform 3d/7d summarization and 14d purge.

    Returns a summary dict with paths processed for each stage.
    """
    processed_3d: list[str] = []
    processed_7d: list[str] = []
    purged_14d: list[str] = []

    for f in list_short_files_due(days=3):
        summarize_to_3d(f)
        processed_3d.append(str(f))
    for f in list_short_files_due(days=7):
        summarize_to_7d(f)
        processed_7d.append(str(f))
    for f in list_short_files_due(days=14):
        purge_14d(f)
        purged_14d.append(str(f))

    return {"summarized_3d": processed_3d, "summarized_7d": processed_7d, "purged_14d": purged_14d}


if __name__ == "__main__":
    stats = daily_maintain()
    print({k: len(v) for k, v in stats.items()})
