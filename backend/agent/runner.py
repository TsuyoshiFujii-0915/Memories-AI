from __future__ import annotations

import os
from typing import Generator, Optional

from openai import OpenAI
from ..config import get_client, model_name


def _get_model() -> str:
    return model_name()


def complete_text(merged_text: str, model: Optional[str] = None) -> tuple[str, dict]:
    """Call OpenAI Responses API and return (text, usage).

    Uses the official OpenAI Python client and the Responses API as per docs.
    """
    client = get_client()
    if client is None:
        # Graceful fallback when not configured
        return ("[Memories-AI] OpenAI client not configured. Set OPENAI_API_KEY or OPENAI_BASE_URL.", {})

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
    client = get_client()
    if client is None:
        yield "data: [Memories-AI] OpenAI client not configured. Set OPENAI_API_KEY or OPENAI_BASE_URL.\n\n"
        yield "event: done\n\n"
        return

    # Responses API streaming
    try:
        with client.responses.stream(model=model or _get_model(), input=merged_text) as stream:
            for event in stream:
                # Events can be dict-like objects; normalize access
                et = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
                if et == "response.output_text.delta":
                    delta = event.get("delta") if isinstance(event, dict) else getattr(event, "delta", "")
                    if delta:
                        yield f"data: {delta}\n\n"
                elif et == "response.completed":
                    break
    except Exception:
        # Fallback: non-stream call
        text, _ = complete_text(merged_text, model=model)
        if text:
            yield f"data: {text}\n\n"
    yield "event: done\n\n"
