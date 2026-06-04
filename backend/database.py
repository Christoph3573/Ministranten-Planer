from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy import text
from typing import Generator

DATABASE_URL = "sqlite:///ministranten.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        try:
            conn.execute(text('ALTER TABLE ministrant ADD COLUMN "alter" INTEGER'))
            conn.commit()
        except Exception:
            pass  # Spalte existiert bereits


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
