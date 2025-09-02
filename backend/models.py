from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Any


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message text")
    sessionId: Optional[str] = Field(default="default", description="Session identifier")


class ChatResponse(BaseModel):
    message: str
    usage: Optional[dict[str, Any]] = None
    memoryActions: Optional[dict[str, Any]] = None


class Message(BaseModel):
    id: str
    role: str
    text: str
    at: str

