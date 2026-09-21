"""Bibliotheksablauf inklusive CSRF, Mail, Bestätigung und PostgreSQL prüfen."""

import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from flask_migrate import check, upgrade
from flask_security import hash_password, verify_password
from sqlalchemy import func, inspect, select
from werkzeug.exceptions import Conflict

from app.data.users.model import User
from app.extensions import db

PASSWORD = "correct horse battery"


def submit(client, path="/register", **values):
    response = client.get(path)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text).group(1)
    return client.post(
        path, data={"csrf_token": token, **values}, headers={"Referer": "https://localhost" + path}
    )


def register(client, username="Lea", email="lea@example.org", password=PASSWORD):
    return submit(
        client, username=username, email=email, password=password, password_confirm=password
    )


def outbox(app):
    return app.extensions["mailman"].outbox


def confirmation(app):
    return re.search(r"https?://[^\s]+/confirm/[^\s]+", outbox(app)[-1].body).group(0)


def test_registration_requires_confirmation_and_stores_only_hash(identity_app):
    client = identity_app.test_client()
    response = register(client)
    assert response.status_code == 302
    with identity_app.app_context():
        user = db.session.scalar(select(User))
        assert user.username == "Lea" and user.email == "lea@example.org"
        assert user.confirmed_at is None
        assert user.password.startswith("$argon2id$")
        assert PASSWORD not in user.password
        assert verify_password(PASSWORD, user.password)
    assert len(outbox(identity_app)) == 1
    assert "Welcome to RepairHub." in outbox(identity_app)[0].body
    assert PASSWORD not in outbox(identity_app)[0].body
    login = submit(client, "/login", identity="lea@example.org", password=PASSWORD)
    assert login.status_code == 200
    with client.session_transaction() as session:
        assert "_user_id" not in session
    assert client.get(confirmation(identity_app)).status_code == 302
    with identity_app.app_context():
        assert db.session.scalar(select(User)).confirmed_at is not None
    assert (
        submit(client, "/login", identity="lea@example.org", password=PASSWORD).status_code == 302
    )
    with client.session_transaction() as session:
        assert "_user_id" in session
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 400
    with identity_app.test_request_context():
        identity = identity_app.extensions["identity_provider"].current()
        assert identity is None
    # Die eigene Präsentation erhält einen DTO statt des Bibliotheks-ORM-Modells.
    with client:
        client.get("/")
        identity = identity_app.extensions["identity_provider"].current()
        assert identity.username == "Lea" and not hasattr(identity, "password")


@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "invalid"),
        ("username", ""),
        ("username", "x" * 81),
        ("password", "1234567"),
        ("password", "x" * 129),
    ],
)
def test_invalid_registration_never_stores_or_echoes_password(identity_app, field, value):
    client = identity_app.test_client()
    data = {"username": "Lea", "email": "lea@example.org", "password": PASSWORD}
    data[field] = value
    response = register(client, **data)
    assert response.status_code == 200
    assert 'class="alert alert-danger"' in response.text
    assert PASSWORD not in response.text
    with identity_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 0


def test_csrf_rejects_missing_and_forged_tokens(identity_app):
    client = identity_app.test_client()
    for token in (None, "forged"):
        data = {"username": "Lea", "email": "lea@example.org", "password": PASSWORD}
        if token:
            data["csrf_token"] = token
        assert client.post("/register", data=data).status_code == 400
    with identity_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize(
    "username,email", [("LEA", "other@example.org"), ("Other", "LEA@example.org")]
)
def test_duplicate_identity_is_rejected_case_insensitively(identity_app, username, email):
    assert register(identity_app.test_client()).status_code == 302
    response = register(identity_app.test_client(), username, email)
    assert response.status_code == 302 and PASSWORD not in response.text
    assert len(outbox(identity_app)) == 2
    with identity_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1


def test_resend_and_invalid_or_expired_confirmation(identity_app, monkeypatch):
    client = identity_app.test_client()
    assert register(client).status_code == 302
    initial = confirmation(identity_app)
    assert client.get(initial + "tampered").status_code == 302
    with identity_app.app_context():
        assert db.session.scalar(select(User)).confirmed_at is None
    # Der Bibliotheks-Serializer erzeugt ein wirklich abgelaufenes signiertes Token.
    from flask_security.confirmable import generate_confirmation_token
    from itsdangerous.timed import TimestampSigner

    with identity_app.app_context(), monkeypatch.context() as patch:
        patch.setattr(TimestampSigner, "get_timestamp", lambda self: 1)
        expired = "/confirm/" + generate_confirmation_token(db.session.scalar(select(User)))
    assert client.get(expired).status_code == 302
    with identity_app.app_context():
        assert db.session.scalar(select(User)).confirmed_at is None
    assert submit(client, "/confirm", email="lea@example.org").status_code == 200
    assert client.get(confirmation(identity_app)).status_code == 302
    # Erneut öffnen darf keine zweite Identität erzeugen.
    client.get(initial)
    with identity_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1


def test_migration_repetition_and_model_match(identity_app):
    with identity_app.app_context():
        upgrade()
        check()
        assert set(inspect(db.engine).get_table_names()) == {
            "users",
            "roles",
            "roles_users",
            "alembic_version",
        }


def test_concurrent_registration_conflict_rolls_back(identity_app):
    barrier = Barrier(2)

    def create(index):
        with identity_app.app_context():
            datastore = identity_app.extensions["security"].datastore
            barrier.wait(timeout=10)
            try:
                datastore.create_user(
                    username="same", email=f"user{index}@example.org", password="hash"
                )
                datastore.commit()
                return "created"
            except Conflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(create, [1, 2])) == ["conflict", "created"]
    with identity_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1
        store = identity_app.extensions["security"].datastore
        store.create_user(username="after", email="after@example.org", password="hash")
        store.commit()
        assert db.session.scalar(select(func.count()).select_from(User)) == 2


def test_password_hashes_are_salted(identity_app):
    with identity_app.app_context():
        one, two = hash_password(PASSWORD), hash_password(PASSWORD)
        assert one != two
        assert verify_password(PASSWORD, one) and verify_password(PASSWORD, two)


def test_smtp_failure_has_no_success_or_partial_user(identity_app, monkeypatch, caplog):
    from flask_mailman.backends.locmem import EmailBackend

    def fail(*args, **kwargs):
        raise OSError("secret-smtp-password")

    monkeypatch.setattr(EmailBackend, "send_messages", fail)
    response = register(identity_app.test_client())
    assert response.status_code == 503
    assert "secret-smtp-password" not in response.text + caplog.text
    with identity_app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("identity", ["lea@example.org", "LEA@example.org", "Lea", "LEA"])
def test_combined_login_accepts_email_or_username(identity_app, identity):
    client = identity_app.test_client()
    register(client)
    client.get(confirmation(identity_app))
    assert submit(client, "/login", identity=identity, password=PASSWORD).status_code == 302
    with client.session_transaction() as session:
        assert "_user_id" in session


@pytest.mark.parametrize(
    "identity,password",
    [("Lea", "incorrect-password"), ("missing-user", PASSWORD), ("", PASSWORD)],
)
def test_combined_login_rejects_invalid_credentials(identity_app, identity, password):
    client = identity_app.test_client()
    register(client)
    client.get(confirmation(identity_app))
    response = submit(client, "/login", identity=identity, password=password)
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert "_user_id" not in session


@pytest.mark.parametrize("next_url", ["https://external.example/", "//external.example/"])
def test_login_ignores_redirect_input_outside_command(identity_app, next_url):
    client = identity_app.test_client()
    register(client)
    client.get(confirmation(identity_app))
    response = submit(client, "/login?next=" + next_url, identity="Lea", password=PASSWORD)
    assert response.status_code == 302
    assert response.location == "/"
