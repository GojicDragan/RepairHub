"""Jeder Identitätstest verwendet ein eigenes PostgreSQL-Schema mit echter Migration."""

import secrets

import pytest
from flask_migrate import upgrade
from sqlalchemy import text

from app import create_app
from app.extensions import db


@pytest.fixture
def identity_app(postgres_app):
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
            upgrade()
        yield application
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()
        with parent_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
