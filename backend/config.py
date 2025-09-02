from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI


_ENV_LOADED = False


def init_env() -> None:
    global _ENV_LOADED
    if not _ENV_LOADED:
        # Load .env if present, but don't fail if it's missing or mock
        load_dotenv(override=False)
        _ENV_LOADED = True


def model_name() -> str:
    return os.getenv("OPENAI_MODEL", os.getenv("MODEL", "gpt-5-mini"))


def base_url() -> Optional[str]:
    # Allow pointing to local OpenAI-compatible servers (e.g., Ollama proxies)
    return os.getenv("OPENAI_BASE_URL") or os.getenv("BASE_URL")


def get_client() -> Optional[OpenAI]:
    """Create an OpenAI client if possible.

    Rules:
    - If OPENAI_BASE_URL is set (e.g., a local proxy), allow missing API key by using a placeholder.
    - If base URL is default (None) and no OPENAI_API_KEY, return None to indicate not configured.
    """
    init_env()
    api_key = os.getenv("OPENAI_API_KEY")
    url = base_url()

    if url:
        # Many local servers ignore api_key; provide a placeholder if missing
        return OpenAI(api_key=api_key or "not-needed", base_url=url)

    if not api_key:
        return None

    return OpenAI(api_key=api_key)
