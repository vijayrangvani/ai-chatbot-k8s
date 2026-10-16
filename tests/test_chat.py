import httpx
from fastapi.testclient import TestClient

from app import main

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
