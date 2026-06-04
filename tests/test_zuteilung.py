import pytest


@pytest.fixture
def setup(client):
    """Create 4 ministranten and 1 termin, return their IDs."""
    names = ["Anna", "Bob", "Clara", "David"]
    m_ids = [client.post("/ministranten", json={"name": n}).json()["id"] for n in names]
    t = client.post("/termine", json={"datum": "2026-01-09", "uhrzeit": "18:00", "anzahl_benoetigt": 2})
    return {"termin_id": t.json()["id"], "ministrant_ids": m_ids}


def test_auto_assign_fills_correct_count(client, setup):
    t_id = setup["termin_id"]
    r = client.post(f"/termine/{t_id}/auto-assign")
    assert r.status_code == 200
    data = r.json()
    assert len(data["zuteilungen"]) == 2


def test_auto_assign_does_not_duplicate(client, setup):
    t_id = setup["termin_id"]
    client.post(f"/termine/{t_id}/auto-assign")
    r2 = client.post(f"/termine/{t_id}/auto-assign")
    assert r2.status_code == 200
    # Still only 2, not 4
    assert len(r2.json()["zuteilungen"]) == 2


def test_auto_assign_skips_inactive(client, setup):
    # Deactivate all ministranten
    for m_id in setup["ministrant_ids"]:
        client.put(f"/ministranten/{m_id}", json={"aktiv": False})
    t_id = setup["termin_id"]
    r = client.post(f"/termine/{t_id}/auto-assign")
    assert r.status_code == 200
    assert len(r.json()["zuteilungen"]) == 0


def test_manual_add_zuteilung(client, setup):
    t_id = setup["termin_id"]
    m_id = setup["ministrant_ids"][0]
    r = client.post(f"/termine/{t_id}/zuteilung", json={"ministrant_id": m_id})
    assert r.status_code == 200
    zuteilungen = r.json()["zuteilungen"]
    assert any(z["ministrant_id"] == m_id for z in zuteilungen)


def test_manual_remove_zuteilung(client, setup):
    t_id = setup["termin_id"]
    m_id = setup["ministrant_ids"][0]
    client.post(f"/termine/{t_id}/zuteilung", json={"ministrant_id": m_id})
    r = client.delete(f"/termine/{t_id}/zuteilung/{m_id}")
    assert r.status_code == 200
    assert not any(z["ministrant_id"] == m_id for z in r.json()["zuteilungen"])


def test_auto_assign_prefers_least_assigned(client, setup):
    """Ministrant with 0 assignments should be picked over one with 1."""
    t_id = setup["termin_id"]
    m_ids = setup["ministrant_ids"]
    # Manually assign Anna to t_id, then create a second termin for the real test
    client.post(f"/termine/{t_id}/zuteilung", json={"ministrant_id": m_ids[0]})  # Anna gets 1
    t2 = client.post("/termine", json={"datum": "2026-01-23", "uhrzeit": "18:00", "anzahl_benoetigt": 1})
    t2_id = t2.json()["id"]
    r = client.post(f"/termine/{t2_id}/auto-assign")
    assigned_ids = [z["ministrant_id"] for z in r.json()["zuteilungen"]]
    assert m_ids[0] not in assigned_ids  # Anna (1 service) should not be picked when others have 0


def test_auto_assign_mixes_jung_and_alt(client):
    # 2 junge (niedriges Alter) + 2 alte (hohes Alter) Ministranten
    jung1 = client.post("/ministranten", json={"name": "Jung1", "alter": 10}).json()["id"]
    jung2 = client.post("/ministranten", json={"name": "Jung2", "alter": 11}).json()["id"]
    alt1 = client.post("/ministranten", json={"name": "Alt1", "alter": 40}).json()["id"]
    alt2 = client.post("/ministranten", json={"name": "Alt2", "alter": 41}).json()["id"]

    termin = client.post("/termine", json={
        "datum": "2026-07-01", "uhrzeit": "10:00", "anzahl_benoetigt": 2
    }).json()

    result = client.post(f"/termine/{termin['id']}/auto-assign", json={})
    assert result.status_code == 200
    assigned_ids = {z["ministrant_id"] for z in result.json()["zuteilungen"]}

    jung_ids = {jung1, jung2}
    alt_ids = {alt1, alt2}
    # Exakt 1 aus jeder Gruppe
    assert len(assigned_ids & jung_ids) == 1
    assert len(assigned_ids & alt_ids) == 1


def test_auto_assign_falls_back_when_only_one_group(client):
    # Nur Ministranten ohne Altersangabe (neutral)
    n1 = client.post("/ministranten", json={"name": "N1"}).json()["id"]
    n2 = client.post("/ministranten", json={"name": "N2"}).json()["id"]

    termin = client.post("/termine", json={
        "datum": "2026-07-02", "uhrzeit": "10:00", "anzahl_benoetigt": 2
    }).json()

    result = client.post(f"/termine/{termin['id']}/auto-assign", json={})
    assert result.status_code == 200
    assert len(result.json()["zuteilungen"]) == 2
