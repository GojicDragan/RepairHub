"""Konfiguration isoliert prüfen, ohne Flask-App oder Datenbankverbindung."""

import secrets

import pytest

from app.config import load_config, validate_config


@pytest.fixture
def valid_config():
    config = load_config()
    config.update(
        REPAIRHUB_ENV="testing",
        TESTING=True,
        SECRET_KEY=secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI="postgresql+psycopg://test:test@127.0.0.1:1/test",
    )
    return config


def test_production_defaults_are_secure(monkeypatch):
    monkeypatch.delenv("REPAIRHUB_ENV", raising=False)
    config = load_config()
    assert config["REPAIRHUB_ENV"] == "production"
    assert config["SESSION_COOKIE_SECURE"] is True
    assert config["SESSION_COOKIE_HTTPONLY"] is True
    assert config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert config["DEBUG"] is False


def test_local_cookie_exception_requires_development(monkeypatch):
    monkeypatch.setenv("REPAIRHUB_ENV", "development")
    assert load_config()["SESSION_COOKIE_SECURE"] is False


@pytest.mark.parametrize("secret", ["", "short", "CHANGE_ME" * 6, None])
def test_rejects_missing_or_placeholder_secret(valid_config, secret):
    valid_config["SECRET_KEY"] = secret
    with pytest.raises(ValueError, match="SECRET_KEY"):
        validate_config(valid_config)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "sqlite:///local.db",
        "postgresql://test:secret@db/test",
        "postgresql+psycopg://test@db/test",
        "postgresql+psycopg://test:secret@db",
        "postgresql+psycopg://test:secret@db:invalid/test",
        "postgresql+psycopg://test:secret@db:70000/test",
        "this secret is not a valid URL",
    ],
)
def test_rejects_invalid_database_without_echoing_credentials(valid_config, url):
    valid_config["SQLALCHEMY_DATABASE_URI"] = url
    with pytest.raises(ValueError, match="DATABASE_URL") as error:
        validate_config(valid_config)
    assert "secret" not in str(error.value)
    assert "sqlite" not in str(error.value)


@pytest.mark.parametrize("override", [{"DEBUG": True}, {"SESSION_COOKIE_SECURE": False}])
def test_production_rejects_unsafe_settings(valid_config, override):
    valid_config.update(REPAIRHUB_ENV="production", TESTING=False)
    valid_config.update(override)
    with pytest.raises(ValueError, match="Production"):
        validate_config(valid_config)


@pytest.mark.parametrize(
    "override",
    [
        {"SESSION_COOKIE_HTTPONLY": False},
        {"SESSION_COOKIE_SAMESITE": None},
        {"REMEMBER_COOKIE_SECURE": False},
        {"REMEMBER_COOKIE_HTTPONLY": False},
        {"REMEMBER_COOKIE_SAMESITE": "None"},
        {"WTF_CSRF_ENABLED": False},
        {"SQLALCHEMY_ECHO": True},
        {"TESTING": True},
    ],
)
def test_production_rejects_other_security_bypasses(valid_config, override):
    valid_config.update(REPAIRHUB_ENV="production", TESTING=False)
    valid_config.update(override)
    with pytest.raises(ValueError, match="Production"):
        validate_config(valid_config)


@pytest.mark.parametrize(
    "settings",
    [
        {"MAIL_USE_TLS": False, "MAIL_USE_SSL": False},
        {"MAIL_BACKEND": "locmem"},
    ],
)
def test_production_cannot_silently_discard_mail_or_send_without_tls(valid_config, settings):
    valid_config.update(REPAIRHUB_ENV="production", TESTING=False, **settings)
    with pytest.raises(ValueError, match="Production"):
        validate_config(valid_config)


def test_development_accepts_both_loopback_hostnames_but_production_does_not(monkeypatch):
    monkeypatch.setenv("PUBLIC_URL", "http://127.0.0.1:8080")
    assert load_config("development")["TRUSTED_HOSTS"] == ["localhost", "127.0.0.1"]
    assert load_config("production")["TRUSTED_HOSTS"] == ["127.0.0.1"]
    monkeypatch.setenv("PUBLIC_URL", "https://example.org")
    assert load_config("development")["TRUSTED_HOSTS"] == ["example.org"]
