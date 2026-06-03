def test_export_docx_returns_file(client):
    client.post("/termine", json={"datum": "2026-01-09", "uhrzeit": "18:00 Uhr", "anzahl_benoetigt": 2})
    r = client.get("/export/docx")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert len(r.content) > 0


def test_export_docx_contains_termin_data(client):
    client.post("/ministranten", json={"name": "Anna"})
    t = client.post("/termine", json={"datum": "2026-01-09", "uhrzeit": "18:00 Uhr", "anzahl_benoetigt": 1})
    t_id = t.json()["id"]
    client.post(f"/termine/{t_id}/auto-assign")

    r = client.get("/export/docx")
    assert r.status_code == 200

    # Parse the returned docx and verify table content
    import io
    from docx import Document
    doc = Document(io.BytesIO(r.content))
    table = doc.tables[0]
    all_text = " ".join(cell.text for row in table.rows for cell in row.cells)
    assert "Anna" in all_text
    assert "09.01.2026" in all_text
