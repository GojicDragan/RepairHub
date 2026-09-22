"""Fehler lassen keine teilweise gespeicherten fachlichen Änderungen zurück."""

from contextlib import contextmanager

from app.extensions import db


@contextmanager
def transaction():
    # Die Identitätsabfrage kann bereits eine Session-Transaktion geöffnet haben.
    try:
        yield
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
