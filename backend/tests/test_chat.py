"""Tests for /api/chat session CRUD (excluding SSE streaming)."""


def test_create_session(client):
    resp = client.post("/api/chat", json={"title": "Test Session"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Session"
    assert "id" in data
    assert data["messages"] == []


def test_create_session_default_title(client):
    resp = client.post("/api/chat", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


def test_list_sessions(client):
    client.post("/api/chat", json={"title": "Session 1"})
    client.post("/api/chat", json={"title": "Session 2"})

    resp = client.get("/api/chat")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_get_session(client):
    create = client.post("/api/chat", json={"title": "Get Me"})
    sid = create.json()["id"]

    resp = client.get(f"/api/chat/{sid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get Me"


def test_get_session_not_found(client):
    resp = client.get("/api/chat/nonexistent-id")
    assert resp.status_code == 404


def test_delete_session(client):
    create = client.post("/api/chat", json={"title": "To Delete"})
    sid = create.json()["id"]

    resp = client.delete(f"/api/chat/{sid}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.get(f"/api/chat/{sid}")
    assert resp.status_code == 404


def test_delete_session_not_found(client):
    resp = client.delete("/api/chat/nonexistent-id")
    assert resp.status_code == 404
