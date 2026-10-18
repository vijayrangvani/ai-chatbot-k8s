import fakeredis
import httpx
from fastapi.testclient import TestClient

from app import cache, main

client = TestClient(main.app)


def test_chat_returns_reply(monkeypatch):
    monkeypatch.setattr(main, "ask_ollama", lambda messages: "fake reply")
    response = client.post("/chat", json={"session_id": "s1", "message": "hi"})

    assert response.status_code == 200
    assert response.json() == {"session_id": "s1", "reply": "fake reply"}


def test_chat_returns_503_when_llm_down(monkeypatch):
    def broken_ollama(messages):
        raise httpx.ConnectError("Ollama is down")

    monkeypatch.setattr(main, "ask_ollama", broken_ollama)
    response = client.post("/chat", json={"session_id": "s1", "message": "hi"})

    assert response.status_code == 503


def test_chat_sends_session_history(monkeypatch):
    received = []

    def fake_ollama(messages):
        received.append(messages)
        return "ok"

    monkeypatch.setattr(main, "ask_ollama", fake_ollama)
    first = client.post("/chat", json={"session_id": "r1", "message": "My colour is blue"})
    second = client.post("/chat", json={"session_id": "r1", "message": "What is my colour?"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert received[1] == [
        {"role": "user", "content": "My colour is blue"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "What is my colour?"},
    ]


def test_chat_cache_miss_fills_cache(monkeypatch):
    monkeypatch.setattr(main, "ask_ollama", lambda messages: "fake reply")
    response = client.post("/chat", json={"session_id": "m1", "message": "hi"})

    assert response.status_code == 200
    assert cache.get_history("m1") == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "fake reply"},
    ]


def test_chat_cache_hit_uses_cached_history(monkeypatch):
    # History exists ONLY in Redis, so if Ollama sees it, the cache was used (not Postgres).
    cached = [
        {"role": "user", "content": "cached question"},
        {"role": "assistant", "content": "cached answer"},
    ]
    cache.append_messages("h1", cached)
    received = []

    def fake_ollama(messages):
        received.append(messages)
        return "ok"

    monkeypatch.setattr(main, "ask_ollama", fake_ollama)
    response = client.post("/chat", json={"session_id": "h1", "message": "new"})

    assert response.status_code == 200
    assert received[0] == [*cached, {"role": "user", "content": "new"}]
    assert len(cache.get_history("h1")) == 4  # hit appends only the 2 new messages


def test_chat_falls_back_to_postgres_when_redis_down(monkeypatch):
    server = fakeredis.FakeServer()
    monkeypatch.setattr(cache, "client", fakeredis.FakeRedis(server=server, decode_responses=True))
    received = []

    def fake_ollama(messages):
        received.append(messages)
        return "ok"

    monkeypatch.setattr(main, "ask_ollama", fake_ollama)
    client.post("/chat", json={"session_id": "d1", "message": "My colour is blue"})
    server.connected = False  # every Redis command now raises ConnectionError
    response = client.post("/chat", json={"session_id": "d1", "message": "What is my colour?"})

    assert response.status_code == 200
    # Redis is unreachable, so this history can only have come from Postgres.
    assert received[1] == [
        {"role": "user", "content": "My colour is blue"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "What is my colour?"},
    ]
