"""Entry point. Run: make run  (or: uvicorn app.main:app --reload)"""

import logging

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import get_settings

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "environment": settings.environment}


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    reply: str


def ask_ollama(messages: list[dict]) -> str:
    """Send this conversation to Ollama and return the assistant's text"""
    response = httpx.post(
        f"{settings.ollama_url}/api/chat",
        json={"model": settings.ollama_model, "messages": messages, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
