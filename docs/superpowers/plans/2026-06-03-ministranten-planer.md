# Ministranten-Planer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app on Raspberry Pi that manages a pool of altar servers, creates service schedules with auto-assignment, and exports them as DOCX.

**Architecture:** FastAPI backend serves both REST API and static frontend files. SQLite via SQLModel stores data. Vanilla JS frontend uses a split-view layout (schedule left, pool right). DOCX export via python-docx mirrors the original table format.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, SQLite, python-docx, Vanilla HTML/CSS/JS, uvicorn, pytest, httpx

---

## File Map

| File | Responsibility |
|------|---------------|
| `backend/models.py` | SQLModel table models + Pydantic response schemas |
| `backend/database.py` | Engine creation, session dependency, `init_db()` |
| `backend/export.py` | `generate_docx(termine)` → BytesIO |
| `backend/main.py` | FastAPI app, all route handlers, mounts `/static` |
| `frontend/index.html` | Single-page shell, modal markup |
| `frontend/style.css` | Dark split-view styles |
| `frontend/app.js` | All fetch calls, state, DOM rendering |
| `tests/conftest.py` | In-memory DB fixture, TestClient fixture |
| `tests/test_ministranten.py` | CRUD tests for /ministranten |
| `tests/test_termine.py` | CRUD tests for /termine |
| `tests/test_zuteilung.py` | Auto-assign + manual assignment tests |
| `tests/test_export.py` | DOCX generation test |
| `requirements.txt` | All Python dependencies |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `backend/__init__.py`
- Create: `tests/__init__.py`
- Create: `frontend/` (empty dir)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend tests frontend
touch backend/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlmodel>=0.0.16
python-docx>=1.1.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: no errors, all packages installed.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt backend/__init__.py tests/__init__.py
git commit -m "chore: project structure and dependencies"
```

---

## Task 2: Database Models

**Files:**
- Create: `backend/models.py`
- Create: `backend/database.py`

- [ ] **Step 1: Create `backend/models.py`**

```python
from __future__ import annotations
from typing import Optional, List
from datetime import date
from sqlmodel import SQLModel, Field, Relationship


# ── Table models ──────────────────────────────────────────────────────────────

class Zuteilung(SQLModel, table=True):
    termin_id: Optional[int] = Field(default=None, foreign_key="termin.id", primary_key=True)
    ministrant_id: Optional[int] = Field(default=None, foreign_key="ministrant.id", primary_key=True)
    termin: Optional["Termin"] = Relationship(back_populates="zuteilungen")
    ministrant: Optional["Ministrant"] = Relationship(back_populates="zuteilungen")


class Ministrant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    aktiv: bool = True
    zuteilungen: List[Zuteilung] = Relationship(back_populates="ministrant")


class Termin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    datum: date
    uhrzeit: str
    priester: Optional[str] = None
    ereignis: Optional[str] = None
    anzahl_benoetigt: int
    zuteilungen: List[Zuteilung] = Relationship(back_populates="termin")


# ── Response schemas (no table=True) ─────────────────────────────────────────

class MinistrantRead(SQLModel):
    id: int
    name: str
    aktiv: bool
    anzahl_zuteilungen: int


class ZuteilungRead(SQLModel):
    ministrant_id: int
    name: str


class TerminRead(SQLModel):
    id: int
    datum: date
    wochentag: str
    uhrzeit: str
    priester: Optional[str]
    ereignis: Optional[str]
    anzahl_benoetigt: int
    zuteilungen: List[ZuteilungRead]


# ── Request schemas ───────────────────────────────────────────────────────────

class MinistrantCreate(SQLModel):
    name: str
    aktiv: bool = True


class MinistrantUpdate(SQLModel):
    name: Optional[str] = None
    aktiv: Optional[bool] = None


class TerminCreate(SQLModel):
    datum: date
    uhrzeit: str
    priester: Optional[str] = None
    ereignis: Optional[str] = None
    anzahl_benoetigt: int


class TerminUpdate(SQLModel):
    datum: Optional[date] = None
    uhrzeit: Optional[str] = None
    priester: Optional[str] = None
    ereignis: Optional[str] = None
    anzahl_benoetigt: Optional[int] = None


WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def get_wochentag(d: date) -> str:
    return WOCHENTAGE[d.weekday()]
```

- [ ] **Step 2: Create `backend/database.py`**

```python
from sqlmodel import create_engine, Session, SQLModel
from typing import Generator

DATABASE_URL = "sqlite:///ministranten.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 3: Write test to verify models can be created**

Create `tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.pool import StaticPool

from backend.database import get_session

# Import app lazily in each test module to avoid circular imports


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    from backend.main import app

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 4: Run a quick import check**

```bash
python -c "from backend.models import Ministrant, Termin, Zuteilung; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/database.py tests/conftest.py
git commit -m "feat: data models and database setup"
```

---

## Task 3: Ministranten CRUD API

**Files:**
- Create: `backend/main.py`
- Create: `tests/test_ministranten.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ministranten.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ministranten.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` because `backend/main.py` doesn't exist yet.

- [ ] **Step 3: Create `backend/main.py` with ministranten routes**

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select, func
from typing import List
import os

from backend.database import get_session, init_db
from backend.models import (
    Ministrant, MinistrantCreate, MinistrantUpdate, MinistrantRead,
    Termin, TerminCreate, TerminUpdate, TerminRead,
    Zuteilung, ZuteilungRead,
    get_wochentag,
)

app = FastAPI(title="Ministranten-Planer")


@app.on_event("startup")
def on_startup():
    init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ministrant_read(m: Ministrant, session: Session) -> MinistrantRead:
    count = session.exec(
        select(func.count()).where(Zuteilung.ministrant_id == m.id)
    ).one()
    return MinistrantRead(
        id=m.id,
        name=m.name,
        aktiv=m.aktiv,
        anzahl_zuteilungen=count,
    )


def _termin_read(t: Termin, session: Session) -> TerminRead:
    session.refresh(t)
    zuteilungen = [
        ZuteilungRead(ministrant_id=z.ministrant_id, name=z.ministrant.name)
        for z in t.zuteilungen
    ]
    return TerminRead(
        id=t.id,
        datum=t.datum,
        wochentag=get_wochentag(t.datum),
        uhrzeit=t.uhrzeit,
        priester=t.priester,
        ereignis=t.ereignis,
        anzahl_benoetigt=t.anzahl_benoetigt,
        zuteilungen=zuteilungen,
    )


# ── Ministranten ──────────────────────────────────────────────────────────────

@app.get("/ministranten", response_model=List[MinistrantRead])
def list_ministranten(session: Session = Depends(get_session)):
    ministranten = session.exec(select(Ministrant)).all()
    return [_ministrant_read(m, session) for m in ministranten]


@app.post("/ministranten", response_model=MinistrantRead)
def create_ministrant(data: MinistrantCreate, session: Session = Depends(get_session)):
    m = Ministrant(name=data.name, aktiv=data.aktiv)
    session.add(m)
    session.commit()
    session.refresh(m)
    return _ministrant_read(m, session)


@app.put("/ministranten/{ministrant_id}", response_model=MinistrantRead)
def update_ministrant(
    ministrant_id: int,
    data: MinistrantUpdate,
    session: Session = Depends(get_session),
):
    m = session.get(Ministrant, ministrant_id)
    if not m:
        raise HTTPException(status_code=404, detail="Ministrant nicht gefunden")
    if data.name is not None:
        m.name = data.name
    if data.aktiv is not None:
        m.aktiv = data.aktiv
    session.add(m)
    session.commit()
    session.refresh(m)
    return _ministrant_read(m, session)


@app.delete("/ministranten/{ministrant_id}", response_model=MinistrantRead)
def delete_ministrant(ministrant_id: int, session: Session = Depends(get_session)):
    m = session.get(Ministrant, ministrant_id)
    if not m:
        raise HTTPException(status_code=404, detail="Ministrant nicht gefunden")
    result = _ministrant_read(m, session)
    # Delete assignments first
    for z in list(m.zuteilungen):
        session.delete(z)
    session.delete(m)
    session.commit()
    return result


# ── Static files (frontend) ───────────────────────────────────────────────────

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
```

- [ ] **Step 4: Run ministranten tests**

```bash
pytest tests/test_ministranten.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_ministranten.py
git commit -m "feat: ministranten CRUD API"
```

---

## Task 4: Termine CRUD API

**Files:**
- Modify: `backend/main.py`
- Create: `tests/test_termine.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_termine.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_termine.py -v
```

Expected: FAIL (no `/termine` routes yet).

- [ ] **Step 3: Add termine routes to `backend/main.py`**

Add after the ministranten section (before the static files mount):

```python
# ── Termine ───────────────────────────────────────────────────────────────────

@app.get("/termine", response_model=List[TerminRead])
def list_termine(session: Session = Depends(get_session)):
    termine = session.exec(select(Termin).order_by(Termin.datum)).all()
    return [_termin_read(t, session) for t in termine]


@app.post("/termine", response_model=TerminRead)
def create_termin(data: TerminCreate, session: Session = Depends(get_session)):
    t = Termin(
        datum=data.datum,
        uhrzeit=data.uhrzeit,
        priester=data.priester,
        ereignis=data.ereignis,
        anzahl_benoetigt=data.anzahl_benoetigt,
    )
    session.add(t)
    session.commit()
    session.refresh(t)
    return _termin_read(t, session)


@app.put("/termine/{termin_id}", response_model=TerminRead)
def update_termin(
    termin_id: int,
    data: TerminUpdate,
    session: Session = Depends(get_session),
):
    t = session.get(Termin, termin_id)
    if not t:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    if data.datum is not None:
        t.datum = data.datum
    if data.uhrzeit is not None:
        t.uhrzeit = data.uhrzeit
    if data.priester is not None:
        t.priester = data.priester
    if data.ereignis is not None:
        t.ereignis = data.ereignis
    if data.anzahl_benoetigt is not None:
        t.anzahl_benoetigt = data.anzahl_benoetigt
    session.add(t)
    session.commit()
    return _termin_read(t, session)


@app.delete("/termine/{termin_id}", response_model=TerminRead)
def delete_termin(termin_id: int, session: Session = Depends(get_session)):
    t = session.get(Termin, termin_id)
    if not t:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    result = _termin_read(t, session)
    for z in list(t.zuteilungen):
        session.delete(z)
    session.delete(t)
    session.commit()
    return result
```

- [ ] **Step 4: Run termine tests**

```bash
pytest tests/test_termine.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run all tests to check for regressions**

```bash
pytest tests/ -v
```

Expected: all 11 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_termine.py
git commit -m "feat: termine CRUD API"
```

---

## Task 5: Zuteilung API (Auto-Assign + Manual)

**Files:**
- Modify: `backend/main.py`
- Create: `tests/test_zuteilung.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_zuteilung.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_zuteilung.py -v
```

Expected: FAIL (no zuteilung routes yet).

- [ ] **Step 3: Add zuteilung routes to `backend/main.py`**

Add the following imports at the top (add to existing import line):

```python
import random
```

Add routes after the termine section (before static files mount):

```python
# ── Zuteilung ─────────────────────────────────────────────────────────────────

class ZuteilungCreate(SQLModel):
    ministrant_id: int


@app.post("/termine/{termin_id}/auto-assign", response_model=TerminRead)
def auto_assign(termin_id: int, session: Session = Depends(get_session)):
    t = session.get(Termin, termin_id)
    if not t:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")

    already_assigned_ids = {z.ministrant_id for z in t.zuteilungen}
    noch_benoetigt = t.anzahl_benoetigt - len(already_assigned_ids)

    if noch_benoetigt <= 0:
        return _termin_read(t, session)

    candidates = session.exec(
        select(Ministrant).where(Ministrant.aktiv == True)
    ).all()
    candidates = [m for m in candidates if m.id not in already_assigned_ids]

    def assignment_count(m: Ministrant) -> int:
        return session.exec(
            select(func.count()).where(Zuteilung.ministrant_id == m.id)
        ).one()

    random.shuffle(candidates)  # random tie-breaking
    candidates.sort(key=assignment_count)  # stable sort: fewest assignments first
    selected = candidates[:noch_benoetigt]

    for m in selected:
        session.add(Zuteilung(termin_id=termin_id, ministrant_id=m.id))
    session.commit()
    session.refresh(t)
    return _termin_read(t, session)


@app.post("/termine/{termin_id}/zuteilung", response_model=TerminRead)
def add_zuteilung(
    termin_id: int,
    data: ZuteilungCreate,
    session: Session = Depends(get_session),
):
    t = session.get(Termin, termin_id)
    if not t:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    m = session.get(Ministrant, data.ministrant_id)
    if not m:
        raise HTTPException(status_code=404, detail="Ministrant nicht gefunden")
    existing = session.get(Zuteilung, (termin_id, data.ministrant_id))
    if not existing:
        session.add(Zuteilung(termin_id=termin_id, ministrant_id=data.ministrant_id))
        session.commit()
    session.refresh(t)
    return _termin_read(t, session)


@app.delete("/termine/{termin_id}/zuteilung/{ministrant_id}", response_model=TerminRead)
def remove_zuteilung(
    termin_id: int,
    ministrant_id: int,
    session: Session = Depends(get_session),
):
    t = session.get(Termin, termin_id)
    if not t:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    z = session.get(Zuteilung, (termin_id, ministrant_id))
    if z:
        session.delete(z)
        session.commit()
    session.refresh(t)
    return _termin_read(t, session)
```

Also add `ZuteilungCreate` to the import block at the top of the file — or just define it inline (it's a small schema, define it in main.py directly as shown above).

- [ ] **Step 4: Run zuteilung tests**

```bash
pytest tests/test_zuteilung.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run all tests**

```bash
pytest tests/ -v
```

Expected: all 17 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_zuteilung.py
git commit -m "feat: zuteilung API with auto-assign"
```

---

## Task 6: DOCX Export

**Files:**
- Create: `backend/export.py`
- Modify: `backend/main.py`
- Create: `tests/test_export.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_export.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_export.py -v
```

Expected: FAIL (no `/export/docx` route yet).

- [ ] **Step 3: Create `backend/export.py`**

```python
import io
from typing import List
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from backend.models import TerminRead


def generate_docx(termine: List[TerminRead]) -> io.BytesIO:
    doc = Document()

    # Title
    if termine:
        date_from = min(t.datum for t in termine).strftime("%d.%m.%Y")
        date_to = max(t.datum for t in termine).strftime("%d.%m.%Y")
        title = doc.add_paragraph(f"Ministrantenplan {date_from} - {date_to}")
        title.runs[0].bold = True
        title.runs[0].font.size = Pt(14)

    doc.add_paragraph("Gerne auch zum ministrieren kommen, wenn ihr nicht eingeteilt seid")

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"

    # Header row
    hdr = table.rows[0].cells
    for cell, text in zip(hdr, ["Datum", "Uhrzeit", "Ministranten", "Ereignis"]):
        cell.text = text
        cell.paragraphs[0].runs[0].bold = True

    # Data rows
    for t in sorted(termine, key=lambda x: x.datum):
        row = table.add_row().cells

        # Datum + Wochentag
        datum_str = t.datum.strftime("%d.%m.%Y")
        row[0].text = f"{datum_str}\n{t.wochentag}"

        # Uhrzeit + Priester
        uhrzeit_str = t.uhrzeit
        if t.priester:
            uhrzeit_str += f"\n{t.priester}"
        row[1].text = uhrzeit_str

        # Ministranten
        if t.zuteilungen:
            row[2].text = " \u2013 ".join(z.name for z in t.zuteilungen)
        else:
            row[2].text = ""

        # Ereignis
        row[3].text = t.ereignis or ""

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
```

- [ ] **Step 4: Add export route to `backend/main.py`**

Add import at the top:
```python
from fastapi.responses import StreamingResponse
from backend.export import generate_docx
```

Add route after the zuteilung section (before static files mount):

```python
# ── Export ────────────────────────────────────────────────────────────────────

@app.get("/export/docx")
def export_docx(session: Session = Depends(get_session)):
    termine = session.exec(select(Termin).order_by(Termin.datum)).all()
    termine_read = [_termin_read(t, session) for t in termine]
    buf = generate_docx(termine_read)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=ministrantenplan.docx"},
    )
```

- [ ] **Step 5: Run export tests**

```bash
pytest tests/test_export.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Run all tests**

```bash
pytest tests/ -v
```

Expected: all 19 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/export.py backend/main.py tests/test_export.py
git commit -m "feat: DOCX export"
```

---

## Task 7: Frontend HTML + CSS

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/style.css`

No automated tests for frontend — verify manually by running the server.

- [ ] **Step 1: Create `frontend/style.css`**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface2: #1c2128;
  --border: #30363d;
  --accent: #e94560;
  --accent2: #4fc3f7;
  --text: #e6edf3;
  --text-muted: #7d8590;
  --chip-bg: #e94560;
  --radius: 6px;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Top bar */
.topbar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.topbar h1 { font-size: 16px; font-weight: 600; }
.topbar .actions { display: flex; gap: 8px; }

/* Buttons */
button {
  cursor: pointer;
  border: none;
  border-radius: var(--radius);
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 500;
  transition: opacity 0.15s;
}
button:hover { opacity: 0.85; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-secondary { background: var(--surface2); color: var(--text-muted); border: 1px solid var(--border); }
.btn-ghost { background: transparent; color: var(--accent2); font-size: 12px; padding: 4px 8px; }
.btn-danger { background: transparent; color: var(--accent); font-size: 11px; padding: 2px 6px; }
.btn-auto { background: var(--surface2); color: var(--accent2); border: 1px solid var(--border); font-size: 11px; padding: 3px 10px; }

/* Split layout */
.split {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Termine panel */
.panel-termine {
  flex: 2;
  display: flex;
  flex-direction: column;
  border-right: 2px solid var(--border);
  overflow: hidden;
}
.panel-header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 8px 16px;
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  flex-shrink: 0;
}
.termine-list {
  overflow-y: auto;
  flex: 1;
}

/* Termin row */
.termin-row {
  border-bottom: 1px solid var(--border);
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.1s;
}
.termin-row:hover { background: var(--surface2); }
.termin-row.selected { background: var(--surface2); border-left: 3px solid var(--accent2); }
.termin-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.termin-title { font-size: 13px; font-weight: 600; }
.termin-time { font-size: 11px; color: var(--text-muted); margin-left: 8px; }
.termin-badge {
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 6px;
}
.termin-count {
  background: var(--surface2);
  color: var(--text-muted);
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 10px;
}
.termin-chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.chip {
  background: var(--accent);
  color: #fff;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.chip .remove {
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  opacity: 0.7;
}
.chip .remove:hover { opacity: 1; }
.chip-missing {
  border: 1px dashed var(--border);
  color: var(--text-muted);
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 12px;
}
.termin-actions { display: flex; gap: 6px; align-items: center; }

/* Pool panel */
.panel-pool {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  overflow: hidden;
}
.pool-header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 8px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.pool-list {
  overflow-y: auto;
  flex: 1;
  padding: 8px;
}
.pool-label {
  font-size: 9px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 4px 4px 8px;
}
.pool-person {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  border-radius: var(--radius);
  margin-bottom: 3px;
  background: var(--surface);
  cursor: pointer;
  transition: background 0.1s;
}
.pool-person:hover { background: var(--surface2); }
.pool-person.inactive { opacity: 0.35; cursor: default; }
.pool-person .name { font-size: 12px; }
.pool-person .count {
  background: var(--surface2);
  color: var(--text-muted);
  font-size: 10px;
  padding: 1px 7px;
  border-radius: 8px;
}
.pool-person .actions-inline { display: flex; gap: 4px; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.modal-overlay.hidden { display: none; }
.modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 24px;
  width: 420px;
  max-width: 95vw;
}
.modal h2 { font-size: 15px; margin-bottom: 16px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.form-group input, .form-group select {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  padding: 8px 10px;
  font-size: 13px;
}
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }

/* Add termin hint */
.add-hint {
  padding: 12px 16px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
  cursor: pointer;
}
.add-hint:hover { color: var(--text); }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
```

- [ ] **Step 2: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ministranten-Planer</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>

  <!-- Top bar -->
  <div class="topbar">
    <h1>⛪ Ministranten-Planer</h1>
    <div class="actions">
      <button class="btn-primary" onclick="openTerminModal()">+ Termin</button>
      <button class="btn-secondary" onclick="exportDocx()">📥 DOCX Export</button>
    </div>
  </div>

  <!-- Split view -->
  <div class="split">

    <!-- Left: Termine -->
    <div class="panel-termine">
      <div class="panel-header">Termine</div>
      <div class="termine-list" id="termine-list">
        <!-- filled by JS -->
      </div>
    </div>

    <!-- Right: Pool -->
    <div class="panel-pool">
      <div class="pool-header">
        <span style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px">Pool</span>
        <button class="btn-ghost" onclick="openPoolModal()">+ Person</button>
      </div>
      <div class="pool-list" id="pool-list">
        <!-- filled by JS -->
      </div>
    </div>

  </div>

  <!-- Termin Modal -->
  <div class="modal-overlay hidden" id="termin-modal">
    <div class="modal">
      <h2 id="termin-modal-title">Termin hinzufügen</h2>
      <div class="form-group">
        <label>Datum</label>
        <input type="date" id="t-datum">
      </div>
      <div class="form-group">
        <label>Uhrzeit</label>
        <input type="text" id="t-uhrzeit" placeholder="z.B. 18:00 Uhr">
      </div>
      <div class="form-group">
        <label>Priester (optional)</label>
        <input type="text" id="t-priester" placeholder="z.B. Pfr. Bula">
      </div>
      <div class="form-group">
        <label>Ereignis (optional)</label>
        <input type="text" id="t-ereignis" placeholder="z.B. Vorstellungsgottesdienst">
      </div>
      <div class="form-group">
        <label>Benötigte Ministranten</label>
        <input type="number" id="t-anzahl" min="1" value="2">
      </div>
      <div class="modal-actions">
        <button class="btn-secondary" onclick="closeTerminModal()">Abbrechen</button>
        <button class="btn-primary" onclick="saveTermin()">Speichern</button>
      </div>
    </div>
  </div>

  <!-- Pool Modal (Add Person) -->
  <div class="modal-overlay hidden" id="pool-modal">
    <div class="modal">
      <h2>Person hinzufügen</h2>
      <div class="form-group">
        <label>Name</label>
        <input type="text" id="p-name" placeholder="Vollständiger Name">
      </div>
      <div class="modal-actions">
        <button class="btn-secondary" onclick="closePoolModal()">Abbrechen</button>
        <button class="btn-primary" onclick="savePool()">Hinzufügen</button>
      </div>
    </div>
  </div>

  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Smoke-test by starting the server and opening the browser**

```bash
cd /path/to/project
uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000` — should see the split-view layout with empty panels and working top bar buttons (modals open/close).

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/style.css
git commit -m "feat: frontend HTML and CSS layout"
```

---

## Task 8: Frontend JavaScript

**Files:**
- Create: `frontend/app.js`

- [ ] **Step 1: Create `frontend/app.js`**

```javascript
// ── State ─────────────────────────────────────────────────────────────────────
let termine = [];
let ministranten = [];
let selectedTerminId = null;
let editingTerminId = null;

// ── API ───────────────────────────────────────────────────────────────────────
const api = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async put(path, body) {
    const r = await fetch(path, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async delete(path) {
    const r = await fetch(path, { method: "DELETE" });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
};

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadAll() {
  [termine, ministranten] = await Promise.all([
    api.get("/termine"),
    api.get("/ministranten"),
  ]);
  renderTermine();
  renderPool();
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderTermine() {
  const container = document.getElementById("termine-list");
  container.innerHTML = "";

  termine.forEach(t => {
    const div = document.createElement("div");
    div.className = "termin-row" + (t.id === selectedTerminId ? " selected" : "");
    div.onclick = () => selectTermin(t.id);

    const assignedCount = t.zuteilungen.length;
    const missing = t.anzahl_benoetigt - assignedCount;
    const dateStr = new Date(t.datum + "T00:00:00").toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
    const titleStr = `${t.wochentag}, ${dateStr}`;
    const timeStr = t.uhrzeit + (t.priester ? ` · ${t.priester}` : "");

    let chipsHtml = t.zuteilungen.map(z => `
      <span class="chip">
        ${z.name}
        <span class="remove" onclick="event.stopPropagation(); removeZuteilung(${t.id}, ${z.ministrant_id})">✕</span>
      </span>`).join("");

    if (missing > 0) {
      chipsHtml += `<span class="chip-missing">+ ${missing} fehlen</span>`;
      chipsHtml += `<button class="btn-auto" onclick="event.stopPropagation(); doAutoAssign(${t.id})">⚡ Auto-Assign</button>`;
    }

    div.innerHTML = `
      <div class="termin-meta">
        <div>
          <span class="termin-title">${titleStr}</span>
          <span class="termin-time">${timeStr}</span>
          ${t.ereignis ? `<span class="termin-badge">${t.ereignis}</span>` : ""}
        </div>
        <div class="termin-actions">
          <span class="termin-count">${assignedCount}/${t.anzahl_benoetigt}</span>
          <button class="btn-ghost" onclick="event.stopPropagation(); openTerminModal(${t.id})">✏️</button>
          <button class="btn-danger" onclick="event.stopPropagation(); deleteTermin(${t.id})">🗑</button>
        </div>
      </div>
      <div class="termin-chips">${chipsHtml}</div>`;
    container.appendChild(div);
  });

  const hint = document.createElement("div");
  hint.className = "add-hint";
  hint.textContent = "+ Termin hinzufügen";
  hint.onclick = () => openTerminModal();
  container.appendChild(hint);
}

function renderPool() {
  const container = document.getElementById("pool-list");
  container.innerHTML = `<div class="pool-label">Nach Diensten sortiert</div>`;

  const active = ministranten.filter(m => m.aktiv).sort((a, b) => a.anzahl_zuteilungen - b.anzahl_zuteilungen);
  const inactive = ministranten.filter(m => !m.aktiv);

  [...active, ...inactive].forEach(m => {
    const div = document.createElement("div");
    div.className = "pool-person" + (!m.aktiv ? " inactive" : "");
    div.onclick = () => m.aktiv && addZuteilungFromPool(m.id);
    div.innerHTML = `
      <span class="name">${m.name}</span>
      <div style="display:flex;gap:6px;align-items:center">
        <span class="count">${m.anzahl_zuteilungen} ×</span>
        <button class="btn-ghost" style="font-size:11px" onclick="event.stopPropagation(); toggleAktiv(${m.id}, ${!m.aktiv})">${m.aktiv ? "⏸" : "▶"}</button>
        <button class="btn-danger" onclick="event.stopPropagation(); deleteMinistrant(${m.id})">✕</button>
      </div>`;
    container.appendChild(div);
  });
}

// ── Actions ───────────────────────────────────────────────────────────────────
function selectTermin(id) {
  selectedTerminId = id;
  renderTermine();
}

async function doAutoAssign(terminId) {
  const updated = await api.post(`/termine/${terminId}/auto-assign`, {});
  termine = termine.map(t => t.id === terminId ? updated : t);
  ministranten = await api.get("/ministranten");
  renderTermine();
  renderPool();
}

async function addZuteilungFromPool(ministrantId) {
  if (!selectedTerminId) return;
  const updated = await api.post(`/termine/${selectedTerminId}/zuteilung`, { ministrant_id: ministrantId });
  termine = termine.map(t => t.id === selectedTerminId ? updated : t);
  ministranten = await api.get("/ministranten");
  renderTermine();
  renderPool();
}

async function removeZuteilung(terminId, ministrantId) {
  const updated = await api.delete(`/termine/${terminId}/zuteilung/${ministrantId}`);
  termine = termine.map(t => t.id === terminId ? updated : t);
  ministranten = await api.get("/ministranten");
  renderTermine();
  renderPool();
}

async function deleteTermin(id) {
  if (!confirm("Termin wirklich löschen?")) return;
  await api.delete(`/termine/${id}`);
  if (selectedTerminId === id) selectedTerminId = null;
  await loadAll();
}

async function deleteMinistrant(id) {
  if (!confirm("Person wirklich löschen?")) return;
  await api.delete(`/ministranten/${id}`);
  await loadAll();
}

async function toggleAktiv(id, aktiv) {
  await api.put(`/ministranten/${id}`, { aktiv });
  ministranten = await api.get("/ministranten");
  renderPool();
}

// ── Termin Modal ──────────────────────────────────────────────────────────────
function openTerminModal(terminId = null) {
  editingTerminId = terminId;
  const t = terminId ? termine.find(x => x.id === terminId) : null;
  document.getElementById("termin-modal-title").textContent = t ? "Termin bearbeiten" : "Termin hinzufügen";
  document.getElementById("t-datum").value = t ? t.datum : "";
  document.getElementById("t-uhrzeit").value = t ? t.uhrzeit : "";
  document.getElementById("t-priester").value = t ? (t.priester || "") : "";
  document.getElementById("t-ereignis").value = t ? (t.ereignis || "") : "";
  document.getElementById("t-anzahl").value = t ? t.anzahl_benoetigt : 2;
  document.getElementById("termin-modal").classList.remove("hidden");
}

function closeTerminModal() {
  document.getElementById("termin-modal").classList.add("hidden");
  editingTerminId = null;
}

async function saveTermin() {
  const body = {
    datum: document.getElementById("t-datum").value,
    uhrzeit: document.getElementById("t-uhrzeit").value,
    priester: document.getElementById("t-priester").value || null,
    ereignis: document.getElementById("t-ereignis").value || null,
    anzahl_benoetigt: parseInt(document.getElementById("t-anzahl").value),
  };
  if (!body.datum || !body.uhrzeit) return alert("Datum und Uhrzeit sind Pflichtfelder.");
  if (editingTerminId) {
    await api.put(`/termine/${editingTerminId}`, body);
  } else {
    await api.post("/termine", body);
  }
  closeTerminModal();
  await loadAll();
}

// ── Pool Modal ────────────────────────────────────────────────────────────────
function openPoolModal() {
  document.getElementById("p-name").value = "";
  document.getElementById("pool-modal").classList.remove("hidden");
}

function closePoolModal() {
  document.getElementById("pool-modal").classList.add("hidden");
}

async function savePool() {
  const name = document.getElementById("p-name").value.trim();
  if (!name) return alert("Name darf nicht leer sein.");
  await api.post("/ministranten", { name, aktiv: true });
  closePoolModal();
  ministranten = await api.get("/ministranten");
  renderPool();
}

// ── Export ────────────────────────────────────────────────────────────────────
function exportDocx() {
  window.location.href = "/export/docx";
}

// ── Close modals on overlay click ─────────────────────────────────────────────
document.getElementById("termin-modal").addEventListener("click", e => {
  if (e.target === e.currentTarget) closeTerminModal();
});
document.getElementById("pool-modal").addEventListener("click", e => {
  if (e.target === e.currentTarget) closePoolModal();
});

// ── Init ──────────────────────────────────────────────────────────────────────
loadAll();
```

- [ ] **Step 2: Start the dev server and test manually**

```bash
uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000` and verify:
1. Add a Termin via the modal — appears in the list
2. Add persons via Pool → + Person — appear in the pool
3. Click ⚡ Auto-Assign on a termin with open spots — ministranten get assigned
4. Click a pool person while a termin is selected — person gets added
5. Click ✕ on a chip — removes that assignment
6. Click 📥 DOCX Export — downloads a `.docx` file
7. Open the `.docx` — verify table matches format of original plan

- [ ] **Step 3: Commit**

```bash
git add frontend/app.js
git commit -m "feat: frontend JavaScript with full API integration"
```

---

## Task 9: Deployment Setup (Raspberry Pi)

**Files:**
- Create: `start.sh`
- Create: `ministranten-planer.service`
- Create: `README.md`

- [ ] **Step 1: Create `start.sh`**

```bash
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

```bash
chmod +x start.sh
```

- [ ] **Step 2: Create `ministranten-planer.service`**

```ini
[Unit]
Description=Ministranten-Planer Web App
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Ministranten-Planer
ExecStart=/home/pi/Ministranten-Planer/start.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Note: Replace `/home/pi/Ministranten-Planer` and `User=pi` with actual path and user on the Raspberry Pi.

To install on the Pi:
```bash
sudo cp ministranten-planer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ministranten-planer
sudo systemctl start ministranten-planer
```

- [ ] **Step 3: Run all tests one final time**

```bash
pytest tests/ -v
```

Expected: all 19 tests PASS.

- [ ] **Step 4: Commit and push**

```bash
git add start.sh ministranten-planer.service README.md
git commit -m "chore: deployment setup for Raspberry Pi"
git push
```

---

## Spec Coverage Check

| Spec requirement | Task |
|-----------------|------|
| Pool of Ministranten (CRUD) | Task 3 |
| Termine erstellen (datum, uhrzeit, priester, ereignis, anzahl) | Task 4 |
| Auto-Assign mit Gleichverteilung | Task 5 |
| Manuell anpassen (hinzufügen/entfernen) | Task 5 |
| Pool-Klick fügt zu selektiertem Termin hinzu | Task 8 |
| Inaktive Ministranten überspringen | Task 5 |
| DOCX-Export im Original-Format | Task 6 |
| Split-View Layout | Task 7 |
| FastAPI + SQLite + python-docx | Task 1–6 |
| Wochentag aus Datum ableiten | Task 2 |
| Raspberry Pi deployment | Task 9 |
