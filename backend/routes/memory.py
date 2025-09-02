from __future__ import annotations

from datetime import date
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

from ..memory.manager import ensure_dirs, retrieve_texts, short_dir, long_dir


router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/short")
def get_short(date_str: str = Query(..., alias="date", description="YYYY-MM-DD")):
    ensure_dirs()
    try:
        d = date.fromisoformat(date_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format")
    p = short_dir() / f"{d.isoformat()}.md"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return {"date": d.isoformat(), "content": p.read_text(encoding="utf-8")}


@router.get("/long")
def get_long():
    ensure_dirs()
    p = long_dir() / "long-term.md"
    if not p.exists():
        return {"content": ""}
    return {"content": p.read_text(encoding="utf-8")}

