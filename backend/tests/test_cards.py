"""Tests for /api/cards CRUD endpoints."""


def test_create_card(client):
    resp = client.post("/api/cards", json={
        "content": "This is a test idea card",
        "tags": ["test", "idea"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "This is a test idea card"
    assert data["tags"] == ["test", "idea"]
    assert "id" in data


def test_list_cards_empty(client):
    resp = client.get("/api/cards")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_cards(client):
    client.post("/api/cards", json={"content": "Card 1", "tags": ["a"]})
    client.post("/api/cards", json={"content": "Card 2", "tags": ["b"]})

    resp = client.get("/api/cards")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_get_card(client):
    create = client.post("/api/cards", json={"content": "Detail card", "tags": []})
    card_id = create.json()["id"]

    resp = client.get(f"/api/cards/{card_id}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "Detail card"


def test_get_card_not_found(client):
    resp = client.get("/api/cards/nonexistent-id")
    assert resp.status_code == 404


def test_update_card(client):
    create = client.post("/api/cards", json={"content": "Original", "tags": ["old"]})
    card_id = create.json()["id"]

    resp = client.put(f"/api/cards/{card_id}", json={
        "content": "Updated content",
        "tags": ["new"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Updated content"
    assert data["tags"] == ["new"]


def test_delete_card(client):
    create = client.post("/api/cards", json={"content": "To delete", "tags": []})
    card_id = create.json()["id"]

    resp = client.delete(f"/api/cards/{card_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.get(f"/api/cards/{card_id}")
    assert resp.status_code == 404


def test_list_tags(client):
    client.post("/api/cards", json={"content": "A", "tags": ["python", "ai"]})
    client.post("/api/cards", json={"content": "B", "tags": ["ai", "web"]})

    resp = client.get("/api/cards/tags")
    assert resp.status_code == 200
    tags = resp.json()
    assert "ai" in tags
    assert "python" in tags
    assert "web" in tags


def test_search_cards(client):
    client.post("/api/cards", json={"content": "Machine learning is great", "tags": []})
    client.post("/api/cards", json={"content": "Web development", "tags": []})

    resp = client.get("/api/cards?search=machine")
    data = resp.json()
    assert data["total"] == 1
    assert "Machine" in data["items"][0]["content"]


def test_pagination(client):
    for i in range(5):
        client.post("/api/cards", json={"content": f"Card {i}", "tags": []})

    resp = client.get("/api/cards?limit=2&offset=0")
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5

    resp = client.get("/api/cards?limit=2&offset=4")
    data = resp.json()
    assert len(data["items"]) == 1
