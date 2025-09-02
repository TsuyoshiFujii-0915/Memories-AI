from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models import ChatRequest, ChatResponse
from ..memory import manager
from ..memory.summarizer import extract_long_fact
from ..agent import runner as agent_runner


router = APIRouter(prefix="/api", tags=["chat"])


def _merge_with_memories(user_text: str) -> str:
    memories = manager.retrieve_texts(days=14)
    merged = (
        "[User Message]\n" + user_text.strip() + "\n\n" +
        "[Memories]\n" + (memories or "(none)") + "\n\n" +
        "指示: ユーザーの入力に丁寧に短く明瞭に日本語で回答してください。"
    )
    return merged


@router.post("/chat", response_model=ChatResponse)
def post_chat(req: ChatRequest) -> ChatResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is empty")

    # Log user message to short-term memory
    manager.log_short("user", req.message)

    # Merge memories and call Responses API
    merged = _merge_with_memories(req.message)
    text, usage = agent_runner.complete_text(merged)

    # Log assistant response
    manager.log_short("ai", text)

    memory_actions: Dict[str, Any] = {}
    try:
        fact = extract_long_fact(f"user: {req.message}\nai: {text}")
        if fact and ":" in fact:
            category, value = fact.split(":", 1)
            res = manager.save_long_fact(value.strip(), category.strip())
            memory_actions = {"long_term": {"extracted": fact.strip(), "result": res}}
    except Exception:
        # Best-effort; ignore extraction failure
        pass

    return ChatResponse(message=text, usage=usage, memoryActions=memory_actions)


@router.get("/chat/stream")
def stream_chat(message: str):
    if not message.strip():
        raise HTTPException(status_code=400, detail="message is empty")

    # Log user message first
    manager.log_short("user", message)

    merged = _merge_with_memories(message)

    def sse_gen():
        for chunk in agent_runner.stream_text(merged):
            yield chunk

    return StreamingResponse(sse_gen(), media_type="text/event-stream")

