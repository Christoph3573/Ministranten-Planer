import pytest
from fastapi.testclient import TestClient


def test_no_credentials_returns_401(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/ministranten")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == 'Basic realm="Ministranten-Planer"'


def test_wrong_password_returns_401(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/ministranten", auth=("admin", "falsch"))
    assert r.status_code == 401


def test_correct_password_allows_access(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/ministranten", auth=("admin", "geheim"))
    assert r.status_code == 200


def test_username_is_ignored(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/ministranten", auth=("beliebig", "geheim"))
    assert r.status_code == 200


def test_missing_env_var_raises_on_startup(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    from backend.main import app
    with pytest.raises(Exception, match="APP_PASSWORD"):
        with TestClient(app):
            pass
