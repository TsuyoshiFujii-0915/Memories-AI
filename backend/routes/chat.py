from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models import ChatRequest, ChatResponse
from ..memory import manager
from ..memory.summarizer import extract_long_fact
from ..agent import character
from ..agent import runner as agent_runner


router = APIRouter(prefix="/api", tags=["chat"])


def _merge_with_memories(user_text: str) -> str:
    # Note: streaming経路の当面のフォールバックとして残す。
    memories = manager.retrieve_texts(days=14)
    merged = (
        "[User Message]\n" + user_text.strip() + "\n\n" +
        "[Memories]\n" + (memories or "(none)") + "\n\n" +
        "指示: ユーザーの入力に丁寧に短く明瞭に日本語で回答してください。"
    )
    return merged


@router.post("/chat", response_model=ChatResponse)
async def post_chat(req: ChatRequest) -> ChatResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is empty")

    # Log user message to short-term memory
    manager.log_short("user", req.message)

    # エージェントに「必要な時だけ思い出す」判断を委ねる
    text = await character.run_turn(user_text=req.message, session_id=req.sessionId or "default")
    usage = {}

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
async def stream_chat(message: str):
    if not message.strip():
        raise HTTPException(status_code=400, detail="message is empty")

    # ユーザー発話を短期メモリへ
    manager.log_short("user", message)

    # まずはエージェントに「必要なら思い出す」下準備のみを委譲
    context = await character.prepare_context(user_text=message, session_id="default")

    # メモリを必要に応じて付加し、Responses API のストリームでトークンを流す
    merged = (
        "[User Message]\n" + message.strip() + "\n\n" +
        "[Memories]\n" + (context or "(none)") + "\n\n" +
        "指示: ユーザーの入力に丁寧に短く明瞭に日本語で回答してください。"
    )

    def sse_gen():
        acc_parts: list[str] = []
        for sse_line in agent_runner.stream_text(merged):
            if sse_line.startswith("data: "):
                acc_parts.append(sse_line[6:].strip("\n"))
                yield sse_line
            else:
                # done の直前に短期/長期メモリへ反映
                final_text = "".join(acc_parts)
                if final_text:
                    manager.log_short("ai", final_text)
                    try:
                        fact = extract_long_fact(f"user: {message}\nai: {final_text}")
                        if fact and ":" in fact:
                            category, value = fact.split(":", 1)
                            manager.save_long_fact(value.strip(), category.strip())
                    except Exception:
                        pass
                yield sse_line

    return StreamingResponse(sse_gen(), media_type="text/event-stream")
