"""Entry point. Run: make run  (or: uvicorn app.main:app --reload)"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import models  # noqa: F401
from app.config import get_settings
from app.db import Base, engine

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    messages = [{"role": "user", "content": request.message}]
    try:
        reply = ask_ollama(messages)
    except httpx.HTTPError as exc:
        log.error("Ollama call failed %s", exc)
        raise HTTPException(status_code=503, detail="LLM Service not available") from exc
    return ChatResponse(session_id=request.session_id, reply=reply)
