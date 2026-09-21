"""Minimale Fixtures; Integrationsprüfungen verwenden ausschliesslich PostgreSQL."""

import os
import secrets

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app_config():
    return {
        "REPAIRHUB_ENV": "testing",
        "TESTING": True,
        "SECRET_KEY": secrets.token_hex(32),
        "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg://test:test@127.0.0.1:1/test",
    }


@pytest.fixture
def app(app_config):
    application = create_app(app_config)
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def postgres_app(app_config):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("CI") == "true":
            pytest.fail("CI verlangt TEST_DATABASE_URL und eine echte PostgreSQL-Testdatenbank.")
        pytest.skip("TEST_DATABASE_URL für echte PostgreSQL-Integration erforderlich.")
    app_config["SQLALCHEMY_DATABASE_URI"] = url
    application = create_app(app_config)
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
