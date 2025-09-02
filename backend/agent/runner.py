from __future__ import annotations

import os
from typing import Generator, Optional

from openai import OpenAI


def _get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-mini")


def complete_text(merged_text: str, model: Optional[str] = None) -> tuple[str, dict]:
    """Call OpenAI Responses API and return (text, usage).

    Uses the official OpenAI Python client and the Responses API as per docs.
    """
    client = OpenAI()
    resp = client.responses.create(model=model or _get_model(), input=merged_text)

    text = ""
    usage = getattr(resp, "usage", None)
    # Extract text from response.output[*].content[*].text (per Responses API)
    output = getattr(resp, "output", None) or []
    for item in output:
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    text = part.get("text") or ""
                    break
    return text, dict(usage or {})


def stream_text(merged_text: str, model: Optional[str] = None) -> Generator[str, None, None]:
    """Yield SSE-formatted chunks using the Responses API streaming.

    Emits lines starting with `data: ` and ends with a final `event: done`.
    """
    client = OpenAI()
    # The Python SDK exposes a streaming interface for Responses API
    # We wrap deltas into SSE lines.
    try:
        with client.responses.stream(model=model or _get_model(), input=merged_text) as stream:
            for event in stream:
                # We expect output_text.delta events (see Responses streaming docs)
                if event.get("type") == "response.output_text.delta":
                    chunk = event.get("delta", "")
                    if chunk:
                        yield f"data: {chunk}\n\n"
                elif event.get("type") == "response.completed":
                    break
    except Exception as e:  # Fallback: non-stream call
        text, _ = complete_text(merged_text, model=model)
        if text:
            yield f"data: {text}\n\n"

    yield "event: done\n\n"

