import base64

import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.pool import StaticPool

from backend.database import get_session


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
def client_fixture(session: Session, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "testpassword")
    from backend.main import app

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    credentials = base64.b64encode(b"admin:testpassword").decode("ascii")
    with TestClient(app, headers={"Authorization": f"Basic {credentials}"}) as c:
        yield c
    app.dependency_overrides.clear()
