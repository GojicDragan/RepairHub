"""Explizite, PostgreSQL-basierte Laufzeitkonfiguration ohne geheime Defaults."""

import os
from collections.abc import Mapping
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def load_config(environment: str | None = None) -> dict[str, Any]:
    environment = (
        environment if environment is not None else os.environ.get("REPAIRHUB_ENV", "production")
    )
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
    }


def validate_config(config: Mapping[str, Any]) -> None:
    if config["REPAIRHUB_ENV"] not in {"production", "development", "testing"}:
        raise ValueError("REPAIRHUB_ENV muss production, development oder testing sein.")
    secret = config["SECRET_KEY"]
    if not isinstance(secret, str) or len(secret) < 32 or secret.startswith("CHANGE_ME"):
        raise ValueError(
            "SECRET_KEY muss ein eigener zufälliger Schlüssel mit mindestens 32 Zeichen sein."
        )
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
        raise ValueError("DATABASE_URL muss eine vollständige PostgreSQL-URL mit psycopg sein.")
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
            config["DEBUG"]
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
                "Produktion verlangt sichere Cookies, CSRF "
                "und deaktivierte Debug-/Test-/SQL-Ausgaben."
            )
