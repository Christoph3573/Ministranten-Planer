from contextlib import asynccontextmanager
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Ministranten-Planer", lifespan=lifespan)


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
