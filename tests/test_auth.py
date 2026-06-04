import pytest
from fastapi.testclient import TestClient


def test_no_credentials_returns_401(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "user")
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/ministranten")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == 'Basic realm="Ministranten-Planer"'


def test_wrong_password_returns_401(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "user")
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/ministranten", auth=("user", "falsch"))
    assert r.status_code == 401


def test_wrong_username_returns_401(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "user")
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/ministranten", auth=("falsch", "geheim"))
    assert r.status_code == 401


def test_correct_credentials_allow_access(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "user")
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/ministranten", auth=("user", "geheim"))
    assert r.status_code == 200


def test_missing_password_env_var_raises_on_startup(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "user")
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    from backend.main import app
    with pytest.raises(Exception, match="APP_PASSWORD"):
        with TestClient(app):
            pass


def test_missing_username_env_var_raises_on_startup(monkeypatch):
    monkeypatch.delenv("APP_USERNAME", raising=False)
    monkeypatch.setenv("APP_PASSWORD", "geheim")
    from backend.main import app
    with pytest.raises(Exception, match="APP_USERNAME"):
        with TestClient(app):
            pass
