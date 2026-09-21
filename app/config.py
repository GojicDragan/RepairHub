"""Explizite, PostgreSQL-basierte Laufzeitkonfiguration ohne geheime Defaults."""

import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def load_config(environment: str | None = None) -> dict[str, Any]:
    environment = (
        environment if environment is not None else os.environ.get("REPAIRHUB_ENV", "production")
    )
    public_url = urlsplit(os.environ.get("PUBLIC_URL", ""))
    trusted_hosts = [public_url.hostname] if public_url.hostname else None
    if environment == "development" and public_url.hostname in {"localhost", "127.0.0.1"}:
        trusted_hosts = ["localhost", "127.0.0.1"]
    return {
        "REPAIRHUB_ENV": environment,
        "SECRET_KEY": os.environ.get("SECRET_KEY", ""),
        "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URL", ""),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ECHO": False,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_ENGINE_OPTIONS": {
            # Alte Pool-Verbindungen nach einem DB-Neustart vor Verwendung prüfen.
            "pool_pre_ping": True,
            "hide_parameters": True,
            # Pool-Wartezeit, Verbindungsaufbau und SQL-Ausführung getrennt begrenzen;
            # keine dieser Fristen allein deckt einen vollständigen Request ab.
            "pool_timeout": 3,
            "connect_args": {"connect_timeout": 3, "options": "-c statement_timeout=3000"},
        },
        "DEBUG": False,
        "TESTING": False,
        "SESSION_COOKIE_SECURE": environment != "development",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "REMEMBER_COOKIE_SECURE": environment != "development",
        "REMEMBER_COOKIE_HTTPONLY": True,
        "REMEMBER_COOKIE_SAMESITE": "Lax",
        "MAX_CONTENT_LENGTH": 1024 * 1024,
        # PUBLIC_URL liefert die öffentliche Adresse für absolute Links, etwa in Mails.
        # Die interne Containeradresse darf nicht beim Empfänger landen.
        "SERVER_NAME": public_url.netloc or None,
        "PREFERRED_URL_SCHEME": public_url.scheme or "https",
        "TRUSTED_HOSTS": trusted_hosts,
        "BABEL_DEFAULT_LOCALE": "en",
        "BABEL_TRANSLATION_DIRECTORIES": "translations",
        "SECURITY_REGISTERABLE": True,
        "SECURITY_CONFIRMABLE": True,
        "SECURITY_CONFIRM_EMAIL_WITHIN": "24 hours",
        "SECURITY_LOGIN_WITHOUT_CONFIRMATION": False,
        "SECURITY_AUTO_LOGIN_AFTER_CONFIRM": False,
        "SECURITY_USERNAME_ENABLE": True,
        "SECURITY_USERNAME_REQUIRED": True,
        "SECURITY_USERNAME_MIN_LENGTH": 1,
        "SECURITY_USERNAME_MAX_LENGTH": 80,
        "SECURITY_USERNAME_NORMALIZE_FORM": "NFC",
        "SECURITY_PASSWORD_LENGTH_MIN": 8,
        "SECURITY_PASSWORD_NORMALIZE_FORM": None,
        "SECURITY_PASSWORD_HASH": "argon2",
        "SECURITY_PASSWORD_SCHEMES": ["argon2"],
        # Argon2 enthält bereits einen individuellen Salt. Kein zusätzlicher
        # HMAC-Pepper, der eine Rotation des Sitzungsschlüssels an Passwörter koppelt.
        "SECURITY_PASSWORD_SINGLE_HASH": ["argon2"],
        # Syntax lokal prüfen; der Bestätigungslink weist den Zugriff auf das Postfach nach.
        # Eine DNS-Abfrage während der Formularprüfung ist dafür nicht erforderlich.
        "SECURITY_EMAIL_VALIDATOR_ARGS": {"check_deliverability": False},
        "SECURITY_REGISTER_URL": "/register",
        "SECURITY_LOGIN_URL": "/login",
        "SECURITY_LOGOUT_URL": "/logout",
        "SECURITY_CONFIRM_URL": "/confirm",
        "SECURITY_LOGOUT_METHODS": ["POST"],
        "SECURITY_POST_REGISTER_VIEW": "web.index",
        "SECURITY_POST_CONFIRM_VIEW": "security.login",
        "SECURITY_POST_LOGIN_VIEW": "web.index",
        "SECURITY_POST_LOGOUT_VIEW": "web.index",
        "SECURITY_RECOVERABLE": True,
        "SECURITY_RESET_URL": "/reset",
        "SECURITY_RESET_PASSWORD_WITHIN": "1 hours",
        "SECURITY_AUTO_LOGIN_AFTER_RESET": False,
        "SECURITY_POST_RESET_VIEW": "security.login",
        "SECURITY_RETURN_GENERIC_RESPONSES": True,
        "SECURITY_CHANGEABLE": False,
        "SECURITY_TRACKABLE": False,
        "SECURITY_SEND_REGISTER_EMAIL": True,
        "SECURITY_EMAIL_SENDER": os.environ.get("MAIL_DEFAULT_SENDER", "noreply@localhost"),
        "MAIL_BACKEND": "locmem" if environment == "testing" else "smtp",
        "MAIL_SERVER": os.environ.get("MAIL_SERVER", "localhost"),
        "MAIL_PORT": int(os.environ.get("MAIL_PORT", "587")),
        "MAIL_USERNAME": os.environ.get("MAIL_USERNAME", ""),
        "MAIL_PASSWORD": os.environ.get("MAIL_PASSWORD", ""),
        "MAIL_USE_TLS": os.environ.get("MAIL_USE_TLS", "true").lower() == "true",
        "MAIL_USE_SSL": os.environ.get("MAIL_USE_SSL", "false").lower() == "true",
        "MAIL_TIMEOUT": 10,
        "MAIL_DEFAULT_SENDER": os.environ.get("MAIL_DEFAULT_SENDER", "noreply@localhost"),
    }


def validate_config(config: Mapping[str, Any]) -> None:
    if config["REPAIRHUB_ENV"] not in {"production", "development", "testing"}:
        raise ValueError("REPAIRHUB_ENV must be production, development or testing.")
    secret = config["SECRET_KEY"]
    if not isinstance(secret, str) or len(secret) < 32 or secret.startswith("CHANGE_ME"):
        raise ValueError("SECRET_KEY must be a unique random key with at least 32 characters.")
    try:
        url = make_url(config["SQLALCHEMY_DATABASE_URI"])
        valid_url = (
            url.drivername == "postgresql+psycopg"
            and url.host
            and url.database
            and url.username
            and url.password
            and (url.port is None or 1 <= url.port <= 65535)
        )
    except (ArgumentError, TypeError, ValueError):
        valid_url = False
    if not valid_url:
        # URL und ursprüngliche Exception können Zugangsdaten enthalten.
        raise ValueError("DATABASE_URL must be a complete PostgreSQL URL using psycopg.")
    if config["MAIL_USE_TLS"] and config["MAIL_USE_SSL"]:
        raise ValueError("MAIL_USE_TLS and MAIL_USE_SSL cannot both be enabled.")
    if not 1 <= config["MAIL_PORT"] <= 65535:
        raise ValueError("MAIL_PORT must be between 1 and 65535.")
    if config["REPAIRHUB_ENV"] == "production":
        required_flags = (
            "SESSION_COOKIE_SECURE",
            "SESSION_COOKIE_HTTPONLY",
            "REMEMBER_COOKIE_SECURE",
            "REMEMBER_COOKIE_HTTPONLY",
            "WTF_CSRF_ENABLED",
        )
        # Nur echte boolesche True-Werte zulassen: Der String "false" ist in
        # Python ebenfalls truthy und darf Sicherheitsflags nicht aktiv erscheinen lassen.
        unsafe = (
            config["MAIL_BACKEND"] != "smtp"
            or not (config["MAIL_USE_TLS"] or config["MAIL_USE_SSL"])
            or config["DEBUG"]
            or config["TESTING"]
            or config["SQLALCHEMY_ECHO"]
            or any(config.get(flag) is not True for flag in required_flags)
            or any(
                config.get(flag) not in {"Lax", "Strict"}
                for flag in (
                    "SESSION_COOKIE_SAMESITE",
                    "REMEMBER_COOKIE_SAMESITE",
                )
            )
        )
        if unsafe:
            raise ValueError(
                "Production requires secure cookies, CSRF, "
                "encrypted SMTP and disabled debug, testing and SQL logging."
            )
