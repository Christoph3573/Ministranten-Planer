import base64
import hmac
import math
import os
import random
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, select, func
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.database import get_session, init_db
from backend.export import generate_docx
from backend.models import (
    Ministrant, MinistrantCreate, MinistrantUpdate, MinistrantRead,
    Termin, TerminCreate, TerminUpdate, TerminRead,
    Zuteilung, ZuteilungRead,
    get_wochentag,
)


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        username: str = request.app.state.username
        password: str = request.app.state.password
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                provided_user, _, provided_pass = decoded.partition(":")
                if hmac.compare_digest(provided_user, username) and hmac.compare_digest(provided_pass, password):
                    return await call_next(request)
            except Exception:
                pass
        return Response(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Ministranten-Planer"'},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    username = os.environ.get("APP_USERNAME")
    if not username:
        raise RuntimeError("APP_USERNAME environment variable is not set")
    password = os.environ.get("APP_PASSWORD")
    if not password:
        raise RuntimeError("APP_PASSWORD environment variable is not set")
    app.state.username = username
    app.state.password = password
    init_db()
    yield


app = FastAPI(title="Ministranten-Planer", lifespan=lifespan)
app.add_middleware(BasicAuthMiddleware)


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
    m = Ministrant(name=data.name, aktiv=data.aktiv, alter=data.alter)
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
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(m, key, value)
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
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(t, key, value)
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

    def sort_group(group):
        random.shuffle(group)
        group.sort(key=lambda m: session.exec(
            select(func.count()).where(Zuteilung.ministrant_id == m.id)
        ).one())
        return group

    with_alter = sorted(
        [m for m in candidates if m.alter is not None],
        key=lambda m: m.alter,
    )
    neutral = [m for m in candidates if m.alter is None]

    n = len(with_alter)
    jung_group = sort_group(with_alter[:n // 2])
    alt_group = sort_group(with_alter[n // 2:])
    neutral = sort_group(neutral)

    need_alt = math.ceil(noch_benoetigt / 2)
    need_jung = noch_benoetigt - need_alt

    selected = alt_group[:need_alt] + jung_group[:need_jung]

    if len(selected) < noch_benoetigt:
        used_ids = {m.id for m in selected}
        fallback = sort_group([
            m for m in neutral + alt_group + jung_group
            if m.id not in used_ids
        ])
        selected += fallback[:noch_benoetigt - len(selected)]

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


# ── Static files (frontend) ───────────────────────────────────────────────────

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
