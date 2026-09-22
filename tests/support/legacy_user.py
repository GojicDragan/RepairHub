"""Historische Migrationsdaten ohne die heutigen ORM-Spalten anlegen."""

import secrets

from flask_security import hash_password
from sqlalchemy import text

from app.extensions import db


def seed_user(username="Lea", password="correct horse battery"):
    user_id = db.session.scalar(
        text(
            "INSERT INTO users(username,email,password,active,fs_uniquifier,confirmed_at) "
            "VALUES (:name,:email,:password,true,:identity,CURRENT_TIMESTAMP) RETURNING id"
        ),
        {
            "name": username,
            "email": username.lower() + "@example.org",
            "password": hash_password(password),
            "identity": secrets.token_hex(16),
        },
    )
    db.session.commit()
    return user_id
