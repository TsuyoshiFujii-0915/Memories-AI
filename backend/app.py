from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.chat import router as chat_router
from .routes.memory import router as memory_router
from .memory.manager import ensure_dirs
from .memory.summarizer import daily_maintain
from .config import init_env


def create_app() -> FastAPI:
    app = FastAPI(title="Memories-AI", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup():
        init_env()
        ensure_dirs()
        # Optional: run maintenance on startup if enabled
        if os.getenv("MEMORY_MAINTAIN_ON_START", "0") in ("1", "true", "True"):
            try:
                daily_maintain()
            except Exception:
                # best-effort; ignore failures at startup
                pass

    @app.get("/")
    def health():
        return {"ok": True, "model": os.getenv("OPENAI_MODEL", "gpt-5-mini")}

    app.include_router(chat_router)
    app.include_router(memory_router)
    return app


app = create_app()
