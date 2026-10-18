# Design decisions

## 001: Redis is a cache; Postgres is the source of truth (2026-10-18)
- **Context:** Every /chat call loaded history from Postgres. Redis lets
  most requests skip the database.
- **Options:** A) If Redis is down, fail the request. B) Fall back to Postgres.
- **Decision:** B. Read from Redis first; on a miss or a Redis error, load
  the last 10 messages from Postgres. On a hit, cache only the 2 new
  messages; on a miss, rebuild the cache from Postgres plus the new ones.
  Commit to Postgres before updating Redis.
- **Why:** Redis is fast, but the chat must keep working without it.
  Committing first means Redis can never hold messages Postgres lacks.
- **Trade-off:** Two stores that can disagree (see 003), and more code.

## 002: Send only the last 10 messages to the LLM (2026-10-18)
- **Context:** Redis keeps 10 messages, but Postgres returned the whole
  history, so a cache hit and a miss sent different context to the LLM.
- **Options:** A) Send everything. B) Send the last 10 on both paths.
- **Decision:** B, using one shared constant (MAX_MESSAGES).
- **Why:** Same behaviour on hit and miss, and small models have a
  limited context window.
- **Trade-off:** The bot forgets anything older than 10 messages.

## 003: Stale Redis cache after a restart (2026-10-18)
- **Context:** If Redis is down, /chat saves to Postgres only. Redis then
  restarts from its disk snapshot, missing those messages, so cache hits
  return incomplete history for up to 1 hour (TTL).
- **Options:** A) disable Redis persistence, B) delete the key when a Redis
  write fails, C) accept and document.
- **Decision:** C locally; A in Kubernetes (Redis without a volume).
- **Why:** The cache is only an optimisation; an empty Redis rebuilds from Postgres.
- **Trade-off:** After a Redis outage, the bot may briefly miss recent messages.
