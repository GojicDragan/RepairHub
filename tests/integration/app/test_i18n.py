"""Englischen Standard und echte gettext-Kataloge an der Präsentationsgrenze prüfen."""

import pytest
from babel.messages.catalog import Catalog
from babel.messages.mofile import write_mo

from app import create_app
from app.extensions import db


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, "en"),
        ("", "en"),
        ("fr-FR", "en"),
        ("de", "de-DE"),
        ("de-CH,de;q=0.9", "de-DE"),
        ("de-AT", "de-DE"),
        ("de-CH,en;q=0.8", "de-DE"),
        ("en-US,de;q=0.8", "en"),
        ("de;q=0,en-US;q=0.8", "en"),
        ("en;q=0,de-CH;q=0.8", "de-DE"),
        ("en-GB", "en"),
        ("de;q=0.5,en;q=0.9", "en"),
        ("fr;q=1,de;q=0.8,en;q=0.5", "de-DE"),
        ("de;q=0,en;q=1", "en"),
        ("*", "en"),
    ],
)
def test_browser_language_negotiation(client, header, expected):
    headers = {"Accept-Language": header} if header is not None else {}
    response = client.get("/register", headers=headers)
    assert response.status_code == 200
    assert response.headers["Content-Language"] == expected
    assert "Accept-Language" in response.vary
    assert f'lang="{expected}"' in response.text
    if expected == "de-DE":
        assert "Konto erstellen" in response.text
        assert "Benutzername" in response.text
        assert "Passwort" in response.text
        assert "Create an account" not in response.text
    else:
        assert "Create an account" in response.text
        assert "Username" in response.text
    assert "/confirm" in response.text


def test_endpoints_are_english_and_not_localized(client):
    for path in ("/register", "/login", "/confirm"):
        assert client.get(path).status_code == 200
    for path in ("/registrieren", "/anmelden", "/bestaetigen", "/abmelden"):
        assert client.get(path).status_code == 404
    assert client.get("/logout").status_code == 405


def test_catalog_translates_ui_and_errors_without_changing_routes(app_config, tmp_path):
    catalog = Catalog(locale="de_DE")
    catalog.add("Manage your personal repairs.", "Verwalten Sie Ihre privaten Reparaturfälle.")
    catalog.add("Page not found", "Seite nicht gefunden")
    directory = tmp_path / "de_DE" / "LC_MESSAGES"
    directory.mkdir(parents=True)
    with (directory / "messages.mo").open("wb") as stream:
        write_mo(stream, catalog)
    application = create_app(
        {
            **app_config,
            "BABEL_DEFAULT_LOCALE": "de",
            "BABEL_TRANSLATION_DIRECTORIES": str(tmp_path),
        }
    )
    try:
        client = application.test_client()
        client.environ_base["HTTP_ACCEPT_LANGUAGE"] = "de"
        home = client.get("/")
        assert 'lang="de-DE"' in home.text
        assert "Verwalten Sie Ihre privaten Reparaturfälle." in home.text
        assert "Seite nicht gefunden" in client.get("/missing").text
        assert client.get("/login").status_code == 200
        assert client.get("/anmelden").status_code == 404
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()


def test_language_is_per_request_and_localizes_api_errors(client):
    german = client.get("/api/missing", headers={"Accept-Language": "de"})
    assert german.json["error"]["title"] == "Seite nicht gefunden"
    english = client.get("/api/missing")
    assert english.json["error"]["title"] == "Page not found"
    assert english.headers["Content-Language"] == "en"
