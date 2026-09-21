"""Passwortwiederherstellung mit Bibliothekstokens, Validierung, CSRF und Sitzungswechsel."""

import re
from urllib.parse import urlsplit

import pytest

from tests.integration.users.test_registration import (
    PASSWORD,
    confirmation,
    outbox,
    register,
    submit,
)

NEW_PASSWORD = "a different secure password"


def reset_link(app):
    return urlsplit(re.search(r"https?://[^\s]+/reset/[^\s]+", outbox(app)[-1].body).group()).path


@pytest.mark.parametrize("language", ["en", "de-CH"])
def test_password_reset_flow_and_single_use(identity_app, language):
    client = identity_app.test_client()
    client.environ_base["HTTP_ACCEPT_LANGUAGE"] = language
    register(client)
    client.get(confirmation(identity_app))
    submit(client, "/login", identity="Lea", password=PASSWORD)
    # Eine bestehende Sitzung behalten, um ihre Entwertung beim Passwortwechsel zu prüfen.
    other = identity_app.test_client()
    other.environ_base["HTTP_ACCEPT_LANGUAGE"] = language
    submit(other, "/reset", email="lea@example.org")
    link = reset_link(identity_app)
    mail = outbox(identity_app)[-1]
    assert NEW_PASSWORD not in mail.body
    assert ("eine Stunde" if language == "de-CH" else "one hour") in mail.body
    assert "#243b35" in mail.alternatives[0][0]
    html = client.get(link).text
    assert 'name="password_confirm"' in html
    assert 'name="username"' not in html
    assert "noindex, nofollow" in html
    assert client.post(link, data={"password": NEW_PASSWORD}).status_code == 400
    response = submit(other, link, password=NEW_PASSWORD, password_confirm=NEW_PASSWORD)
    assert response.status_code == 302
    assert response.location.endswith("/login")
    assert 'name="password_confirm"' not in other.get(link, follow_redirects=True).text
    assert (
        "Dein Passwort wurde zurückgesetzt"
        if language == "de-CH"
        else "Your password has been reset"
    ) in outbox(identity_app)[-1].body
    assert submit(other, "/login", identity="Lea", password=PASSWORD).status_code == 200
    assert submit(other, "/login", identity="Lea", password=NEW_PASSWORD).status_code == 302
    assert 'name="identity"' in client.get("/login", follow_redirects=True).text


def test_reset_unknown_address_has_generic_response_and_sends_nothing(identity_app):
    client = identity_app.test_client()
    response = submit(client, "/reset", email="unknown@example.org")
    assert response.status_code == 200
    assert not getattr(identity_app.extensions["mailman"], "outbox", [])
    assert "does not exist" not in response.text


@pytest.mark.parametrize(
    "password,confirmation_value",
    [("short", "short"), (NEW_PASSWORD, "different"), ("x" * 129, "x" * 129)],
)
def test_reset_rejects_invalid_password(identity_app, password, confirmation_value):
    client = identity_app.test_client()
    register(client)
    client.get(confirmation(identity_app))
    submit(client, "/reset", email="lea@example.org")
    link = reset_link(identity_app)
    assert (
        submit(client, link, password=password, password_confirm=confirmation_value).status_code
        == 200
    )
    assert len(outbox(identity_app)) == 2


def test_reset_rejects_tampered_and_expired_tokens(identity_app, monkeypatch):
    client = identity_app.test_client()
    register(client)
    client.get(confirmation(identity_app))
    submit(client, "/reset", email="lea@example.org")
    link = reset_link(identity_app)
    assert client.get(link + "tampered").status_code == 302
    import time

    now = time.time()
    monkeypatch.setattr("itsdangerous.timed.time.time", lambda: now + 3601)
    assert client.get(link).status_code == 302
