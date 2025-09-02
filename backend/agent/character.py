from __future__ import annotations

import os
from typing import Optional

from agents import Agent, Runner, function_tool, SQLiteSession

from ..memory.manager import retrieve_texts, save_long_fact


BASE_INSTRUCTIONS = (
    "あなたは丁寧で親しみやすい一般的な女性キャラクターです。"
    "ユーザーの心情に配慮し、短く明瞭に回答してください。"
    "必要だと思ったときだけ、retrieve_memories ツールで過去の短期/長期メモリを取り出してから回答を続けてください。"
)


@function_tool
def retrieve_memories(query: Optional[str] = None, days: Optional[int] = 14) -> str:
    """短期/長期メモリから関連テキストを収集して返します。"""
    return retrieve_texts(query=query, days=days or 14)


@function_tool
def save_long_term_memory(text: str, category: Optional[str] = None) -> str:
    """重要/反復/印象的な事項を極小要約として long-term.md に追記します。"""
    return save_long_fact(text=text, category=category)


def build_agent(model: Optional[str] = None, instructions: Optional[str] = None) -> Agent:
    return Agent(
        name="Assistant",
        instructions=instructions or BASE_INSTRUCTIONS,
        model=model or os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        tools=[retrieve_memories, save_long_term_memory],
    )


async def run_turn(user_text: str, session_id: str = "default", model: Optional[str] = None, instructions: Optional[str] = None) -> str:
    agent = build_agent(model=model, instructions=instructions)
    session = SQLiteSession(session_id)
    result = await Runner.run(agent, user_text, session=session)
    return str(result.final_output or "")

