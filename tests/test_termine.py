from datetime import date


def test_list_termine_empty(client):
    r = client.get("/termine")
    assert r.status_code == 200
    assert r.json() == []


def test_create_termin(client):
    r = client.post("/termine", json={
        "datum": "2026-01-09",
        "uhrzeit": "18:00 Uhr",
        "anzahl_benoetigt": 2,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["datum"] == "2026-01-09"
    assert data["wochentag"] == "Freitag"
    assert data["uhrzeit"] == "18:00 Uhr"
    assert data["priester"] is None
    assert data["ereignis"] is None
    assert data["anzahl_benoetigt"] == 2
    assert data["zuteilungen"] == []


def test_create_termin_with_priester_and_ereignis(client):
    r = client.post("/termine", json={
        "datum": "2026-01-25",
        "uhrzeit": "8:30 Uhr",
        "priester": "Pfr. Bula",
        "ereignis": "Vorstellungsgottesdienst",
        "anzahl_benoetigt": 4,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["wochentag"] == "Sonntag"
    assert data["priester"] == "Pfr. Bula"
    assert data["ereignis"] == "Vorstellungsgottesdienst"


def test_update_termin(client):
    r = client.post("/termine", json={"datum": "2026-02-06", "uhrzeit": "18:00 Uhr", "anzahl_benoetigt": 2})
    id_ = r.json()["id"]
    r2 = client.put(f"/termine/{id_}", json={"anzahl_benoetigt": 3, "priester": "Pfr. Bula"})
    assert r2.status_code == 200
    assert r2.json()["anzahl_benoetigt"] == 3
    assert r2.json()["priester"] == "Pfr. Bula"


def test_delete_termin(client):
    r = client.post("/termine", json={"datum": "2026-03-01", "uhrzeit": "08:30", "anzahl_benoetigt": 2})
    id_ = r.json()["id"]
    r2 = client.delete(f"/termine/{id_}")
    assert r2.status_code == 200
    r3 = client.get("/termine")
    assert not any(t["id"] == id_ for t in r3.json())


def test_termine_sorted_by_date(client):
    client.post("/termine", json={"datum": "2026-03-06", "uhrzeit": "18:00", "anzahl_benoetigt": 2})
    client.post("/termine", json={"datum": "2026-01-09", "uhrzeit": "18:00", "anzahl_benoetigt": 2})
    r = client.get("/termine")
    dates = [t["datum"] for t in r.json()]
    assert dates == sorted(dates)
