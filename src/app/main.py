"""Entry point. Run: make run  (or: uvicorn app.main:app --reload)"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import MAX_MESSAGES, append_messages, get_history
from app.config import get_settings
from app.db import Base, DbSession, engine
from app.models import Message

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


def load_recent_history(db: Session, session_id: str) -> list[dict]:
    """Last MAX_MESSAGES messages from Postgres, oldest first."""
    # Newest-first + LIMIT picks the most recent rows; reversed() restores chronological order.
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id.desc())
        .limit(MAX_MESSAGES)
    ).all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: DbSession) -> ChatResponse:
    cached = get_history(request.session_id)
    # None = cache miss or Redis down; Postgres is the source of truth either way.
    history = cached if cached is not None else load_recent_history(db, request.session_id)

    messages = [*history, {"role": "user", "content": request.message}]
    try:
        reply = ask_ollama(messages)
    except httpx.HTTPError as exc:
        log.error("Ollama call failed %s", exc)
        raise HTTPException(status_code=503, detail="LLM Service not available") from exc

    db.add(Message(session_id=request.session_id, role="user", content=request.message))
    db.add(Message(session_id=request.session_id, role="assistant", content=reply))
    # Commit BEFORE caching so Redis never holds messages that Postgres doesn't.
    db.commit()

    new_messages = [
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": reply},
    ]
    # Hit: cache already has the history. Miss: rebuild it from Postgres + the new pair.
    append_messages(
        request.session_id, new_messages if cached is not None else history + new_messages
    )

    return ChatResponse(session_id=request.session_id, reply=reply)
