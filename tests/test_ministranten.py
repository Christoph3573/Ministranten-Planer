def test_list_ministranten_empty(client):
    r = client.get("/ministranten")
    assert r.status_code == 200
    assert r.json() == []


def test_create_ministrant(client):
    r = client.post("/ministranten", json={"name": "Anna", "aktiv": True})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Anna"
    assert data["aktiv"] is True
    assert data["anzahl_zuteilungen"] == 0
    assert "id" in data


def test_update_ministrant(client):
    r = client.post("/ministranten", json={"name": "Bob"})
    id_ = r.json()["id"]
    r2 = client.put(f"/ministranten/{id_}", json={"aktiv": False})
    assert r2.status_code == 200
    assert r2.json()["aktiv"] is False


def test_delete_ministrant(client):
    r = client.post("/ministranten", json={"name": "Zu löschen"})
    id_ = r.json()["id"]
    r2 = client.delete(f"/ministranten/{id_}")
    assert r2.status_code == 200
    r3 = client.get("/ministranten")
    assert not any(m["id"] == id_ for m in r3.json())


def test_delete_nonexistent_ministrant(client):
    r = client.delete("/ministranten/9999")
    assert r.status_code == 404
