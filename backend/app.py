from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.chat import router as chat_router
from .routes.memory import router as memory_router
from .memory.manager import ensure_dirs
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

    @app.get("/")
    def health():
        return {"ok": True, "model": os.getenv("OPENAI_MODEL", "gpt-5-mini")}

    app.include_router(chat_router)
    app.include_router(memory_router)
    return app


app = create_app()
