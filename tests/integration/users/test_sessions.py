"""T05: echte Sitzungen und Identitätsgrenzen mit PostgreSQL und aktiver CSRF-Prüfung."""

import re
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.data.users.model import User
from app.domains.users.dto import UserIdentity
from app.extensions import db
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit


@pytest.fixture
def account(identity_app):
    client = identity_app.test_client()
    assert register(client).status_code == 302
    assert client.get(confirmation(identity_app)).status_code == 302
    return client


def identity(app, client):
    # Den tatsächlich verdrahteten Port innerhalb eines echten Requests abfragen.
    # Es wird keine vorgezogene Gerätefunktion als geschützter Endpunkt erfunden.
    with client:
        client.get("/")
        return app.extensions["identity_provider"].current()


def token(client):
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', client.get("/").text).group(1)


def login(client, **overrides):
    return submit(client, "/login", **{"identity": "Lea", "password": PASSWORD, **overrides})


def test_login_exposes_only_verified_identity_and_logout_removes_it(identity_app, account):
    assert identity(identity_app, account) is None
    assert login(account).status_code == 302
    viewer = identity(identity_app, account)
    assert isinstance(viewer, UserIdentity) and viewer.username == "Lea"
    assert vars(viewer) == {"id": viewer.id, "username": "Lea"}
    csrf = token(account)
    response = account.post(
        "/logout", data={"csrf_token": csrf}, headers={"Referer": "https://localhost/"}
    )
    assert response.status_code == 302
    assert identity(identity_app, account) is None
    with account.session_transaction() as session:
        assert "_user_id" not in session
        assert "csrf_token" not in session
    assert 'name="identity"' in account.get("/login").text


@pytest.mark.parametrize("path", ["/login", "/logout"])
@pytest.mark.parametrize("csrf", [None, "tampered", "another-session"])
def test_csrf_failure_cannot_change_authentication(identity_app, account, path, csrf):
    if path == "/logout":
        assert login(account).status_code == 302
    if csrf == "another-session":
        page = identity_app.test_client().get("/login")
        csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page.text).group(1)
    values = {"identity": "Lea", "password": PASSWORD}
    if csrf is not None:
        values["csrf_token"] = csrf
    response = account.post(path, data=values, headers={"Referer": "https://localhost/"})
    assert response.status_code == 400
    assert (identity(identity_app, account) is not None) == (path == "/logout")
    assert PASSWORD not in response.text


@pytest.mark.parametrize("cookie_name", ["session", "remember_token"])
def test_tampered_cookie_never_provides_identity(identity_app, account, cookie_name):
    assert login(account, remember="y").status_code == 302
    cookie = account.get_cookie(cookie_name)
    assert cookie is not None
    attacker = identity_app.test_client()
    attacker.set_cookie(cookie_name, cookie.value + "tampered")
    assert identity(identity_app, attacker) is None
    assert 'name="identity"' in attacker.get("/login").text


def test_remember_cookie_restores_identity_and_logout_clears_it(identity_app, account):
    assert login(account, remember="y").status_code == 302
    assert account.get_cookie("remember_token") is not None
    account.delete_cookie("session")
    assert identity(identity_app, account).username == "Lea"
    response = account.post(
        "/logout", data={"csrf_token": token(account)}, headers={"Referer": "https://localhost/"}
    )
    assert response.status_code == 302
    assert account.get_cookie("remember_token") is None
    assert identity(identity_app, account) is None


@pytest.mark.parametrize("remember", [False, True])
def test_cookies_have_secure_attributes_and_contain_no_password(identity_app, account, remember):
    response = login(account, remember="y" if remember else "")
    cookies = response.headers.getlist("Set-Cookie")
    for name in ("session", "remember_token") if remember else ("session",):
        value = next(item for item in cookies if item.startswith(name + "="))
        assert "Secure" in value and "HttpOnly" in value and "SameSite=Lax" in value
        assert PASSWORD not in value
    if not remember:
        assert account.get_cookie("remember_token") is None


@pytest.mark.parametrize("change", ["inactive", "unconfirmed", "rotated"])
def test_existing_session_cannot_bypass_current_identity_state(identity_app, account, change):
    assert login(account).status_code == 302
    with identity_app.app_context():
        user = db.session.scalar(select(User))
        if change == "inactive":
            user.active = False
        elif change == "unconfirmed":
            user.confirmed_at = None
        else:
            identity_app.extensions["security"].datastore.set_uniquifier(user)
        db.session.commit()
    assert identity(identity_app, account) is None


def test_inactive_account_cannot_log_in(identity_app, account):
    with identity_app.app_context():
        user = db.session.scalar(select(User))
        user.active = False
        user.confirmed_at = datetime.now(UTC)
        db.session.commit()
    assert login(account).status_code == 200
    assert identity(identity_app, account) is None


@pytest.mark.parametrize("username,password", [("Lea", "wrong-secret"), ("unknown", PASSWORD)])
def test_login_errors_never_echo_password_or_create_session(
    identity_app, account, username, password
):
    response = login(account, identity=username, password=password)
    assert response.status_code == 200
    assert password not in response.text
    assert re.search(r'<input[^>]*name="password"[^>]*value=""', response.text)
    assert identity(identity_app, account) is None
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
