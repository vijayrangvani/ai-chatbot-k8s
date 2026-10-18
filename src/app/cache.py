"""Redis cache for recent chat history. Never raises: on any Redis error it logs and degrades.

Shape to remember:
    key "chat:{session_id}" -> Redis LIST of JSON messages, oldest first, max 10, TTL 1 hour.
"""

import json
import logging

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.config import get_settings

log = logging.getLogger(__name__)

MAX_MESSAGES = 10
TTL_SECONDS = 3600
REDIS_TIMEOUT_S = 1  # a dead Redis must not stall a request

# Client = connection pool. Create ONCE per process; it connects lazily on the first command.
client = redis.Redis.from_url(
    get_settings().redis_url,
    socket_connect_timeout=REDIS_TIMEOUT_S,
    socket_timeout=REDIS_TIMEOUT_S,
    # redis-py retries 3x with backoff by default, which would multiply the timeout above.
    retry=Retry(NoBackoff(), 0),
    decode_responses=True,  # return str instead of bytes
)


def _key(session_id: str) -> str:
    return f"chat:{session_id}"


def get_history(session_id: str) -> list[dict] | None:
    """Cached messages, oldest first, or None on a cache miss or any Redis error."""
    try:
        raw = client.lrange(_key(session_id), 0, -1)
        # Redis deletes empty lists, so an empty result means the key doesn't exist.
        if not raw:
            return None
        return [json.loads(item) for item in raw]
    except (redis.RedisError, ValueError) as exc:  # ValueError covers corrupt JSON
        log.warning("Redis get_history failed for session %s: %s", session_id, exc)
        return None


def append_messages(session_id: str, messages: list[dict]) -> None:
    """Append messages, keep only the last MAX_MESSAGES, reset TTL. Does nothing on error."""
    if not messages:
        return
    key = _key(session_id)
    try:
        # MULTI/EXEC: push + trim + expire apply together, in one round trip.
        with client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, *(json.dumps(m) for m in messages))
            pipe.ltrim(key, -MAX_MESSAGES, -1)
            pipe.expire(key, TTL_SECONDS)
            pipe.execute()
    except redis.RedisError as exc:
        log.warning("Redis append_messages failed for session %s: %s", session_id, exc)
