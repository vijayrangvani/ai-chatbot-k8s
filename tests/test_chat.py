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
