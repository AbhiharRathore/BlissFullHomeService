"""CSRF protection and basic page loads, against a throwaway SQLite database."""

import re

import pytest

TOKEN = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.sqlite3'}")
    from PROJECT import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def token_from(client, path):
    return TOKEN.search(client.get(path).get_data(as_text=True)).group(1)


def test_forms_carry_a_token(app):
    assert TOKEN.search(app.test_client().get("/admin/login").get_data(as_text=True))


@pytest.mark.parametrize("token", [None, "forged"])
def test_post_without_a_valid_token_is_rejected(app, token):
    data = {"username": "admin", "password": "admin123"}
    if token:
        data["csrf_token"] = token
    assert app.test_client().post("/admin/login", data=data).status_code == 400


def test_post_with_the_session_token_works(app):
    c = app.test_client()
    r = c.post("/admin/login", data={"username": "admin", "password": "admin123",
                                     "csrf_token": token_from(c, "/admin/login")}, follow_redirects=True)
    assert r.status_code == 200 and r.request.path == "/admin/dashboard"


def test_token_from_another_session_is_rejected(app):
    stolen = token_from(app.test_client(), "/admin/login")
    other = app.test_client()
    other.get("/login/user")
    assert other.post("/login/user", data={"username": "x", "password": "y", "csrf_token": stolen}).status_code == 400


@pytest.mark.parametrize("path", ["/", "/login/user", "/signup/user", "/service_professional/login"])
def test_public_pages_load(app, path):
    assert app.test_client().get(path).status_code == 200
