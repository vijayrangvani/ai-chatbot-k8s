"""Entry point. Run: make run  (or: uvicorn app.main:app --reload)"""

import logging

from fastapi import FastAPI

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
