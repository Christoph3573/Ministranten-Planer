from typing import Optional, List, TYPE_CHECKING
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
    alter: Optional[int] = Field(default=None)
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
    alter: Optional[int] = None


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
