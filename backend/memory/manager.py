from __future__ import annotations

import json
import os
import re
import hashlib
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List, Dict


def memory_root() -> Path:
    return Path(os.getenv("MEMORY_ROOT", "./memory")).resolve()


def short_dir() -> Path:
    return memory_root() / "short"


def long_dir() -> Path:
    return memory_root() / "long"


def index_path() -> Path:
    return memory_root() / "index.json"


def ensure_dirs() -> None:
    short_dir().mkdir(parents=True, exist_ok=True)
    long_dir().mkdir(parents=True, exist_ok=True)
    if not index_path().exists():
        index_path().write_text(json.dumps({"files": {}}, ensure_ascii=False, indent=2))
    # Ensure long-term file exists
    lt = long_dir() / "long-term.md"
    if not lt.exists():
        lt.write_text("# Long-term Memories\n\n", encoding="utf-8")


def _daily_file_path(d: date) -> Path:
    return short_dir() / f"{d.isoformat()}.md"


def _load_index() -> Dict:
    try:
        return json.loads(index_path().read_text())
    except Exception:
        return {"files": {}}


def _save_index(data: Dict) -> None:
    index_path().write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _update_index_for_date(d: date) -> None:
    idx = _load_index()
    ds = d.isoformat()
    if ds not in idx.get("files", {}):
        created = datetime.combine(d, datetime.min.time()).isoformat()
        idx.setdefault("files", {})[ds] = {
            "created_at": created,
            "state": "raw",
            "due_3d": (d + timedelta(days=3)).isoformat(),
            "due_7d": (d + timedelta(days=7)).isoformat(),
            "due_14d": (d + timedelta(days=14)).isoformat(),
        }
        _save_index(idx)


def log_short(role: str, text: str, at: Optional[datetime] = None) -> Path:
    """Append a line to today's short-term memory file."""
    ensure_dirs()
    now = at or datetime.now()
    d = now.date()
    path = _daily_file_path(d)
    if not path.exists():
        path.write_text(f"# {d.isoformat()} (short-term)\n\n", encoding="utf-8")
    hhmm = now.strftime("%H:%M")
    line = f"- [{hhmm}] {role}: {text}\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
    _update_index_for_date(d)
    return path


def retrieve_texts(query: Optional[str] = None, days: int = 14) -> str:
    """Collect recent short-term and long-term memory as Markdown text.

    If query is provided, filter lines containing the query (case-insensitive).
    """
    ensure_dirs()
    cutoff = datetime.now().date() - timedelta(days=days)
    parts: List[str] = []

    # Short-term files
    for p in sorted(short_dir().glob("*.md")):
        try:
            d = date.fromisoformat(p.stem)
        except Exception:
            continue
        if d < cutoff:
            continue
        content = p.read_text(encoding="utf-8")
        if query:
            filtered = []
            for line in content.splitlines():
                if query.lower() in line.lower():
                    filtered.append(line)
            if filtered:
                parts.append(f"## {p.name}\n" + "\n".join(filtered))
        else:
            parts.append(content)

    # Long-term file
    lt = long_dir() / "long-term.md"
    if lt.exists():
        content = lt.read_text(encoding="utf-8")
        if query:
            filt = []
            for line in content.splitlines():
                if query.lower() in line.lower():
                    filt.append(line)
            if filt:
                parts.append("## long-term.md\n" + "\n".join(filt))
        else:
            parts.append("## long-term.md\n" + content)

    return "\n\n".join(parts).strip()


def _fingerprint(text: str, category: Optional[str]) -> str:
    norm = re.sub(r"\s+", " ", (category or "") + "|" + (text or "")).strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def save_long_fact(text: str, category: Optional[str] = None) -> str:
    """Append a concise long-term fact with date and fingerprint; avoid duplicates."""
    ensure_dirs()
    today = datetime.now().date().isoformat()
    fp = _fingerprint(text, category)
    lt = long_dir() / "long-term.md"
    existing = lt.read_text(encoding="utf-8") if lt.exists() else ""
    if fp in existing:
        return f"duplicate(fp:{fp})"
    tag = {
        "like": "#likes",
        "dislike": "#dislikes",
        "habit": "#habits",
        "other": "#other",
    }.get((category or "other").lower(), "#other")
    line = f"- {today} | {category or 'other'}: {text} | {tag} | fp:{fp}\n"
    with lt.open("a", encoding="utf-8") as f:
        f.write(line)
    return f"saved(fp:{fp})"


def list_short_files_due(days: int) -> List[Path]:
    """Return paths for short files whose due_[days] is reached or passed."""
    ensure_dirs()
    now_d = datetime.now().date()
    key = {3: "due_3d", 7: "due_7d", 14: "due_14d"}.get(days)
    if not key:
        return []
    idx = _load_index().get("files", {})
    due_list: List[Path] = []
    for ds, meta in idx.items():
        try:
            due = date.fromisoformat(meta.get(key, ""))
            d = date.fromisoformat(ds)
        except Exception:
            continue
        if d > now_d:
            continue
        if now_d >= due:
            p = _daily_file_path(d)
            if p.exists():
                due_list.append(p)
    return sorted(due_list)

