"""Minimale Fixtures; Integrationsprüfungen verwenden ausschliesslich PostgreSQL."""

import os
import secrets

import pytest
from flask_migrate import upgrade
from sqlalchemy import text

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


@pytest.fixture
def identity_app(postgres_app, request):
    schema = "registration_" + secrets.token_hex(8)
    with postgres_app.app_context():
        parent_engine = db.engine
        with parent_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    config = dict(postgres_app.config)
    config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "hide_parameters": True,
        "connect_args": {"options": f"-c search_path={schema}"},
    }
    application = create_app(config)
    try:
        with application.app_context():
            upgrade(revision=getattr(request, "param", "head"))
        yield application
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()
        with parent_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
