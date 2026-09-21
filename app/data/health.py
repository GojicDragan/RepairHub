"""Rein technische Datenbankdiagnose ohne fachliche Abfragen."""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


def database_ready() -> bool:
    """Eine echte PostgreSQL-Verbindung prüfen und immer freigeben."""
    try:
        # Eine kurzlebige Verbindung statt der fachlichen Session verwenden:
        # Der Check soll keine laufende Fachtransaktion öffnen oder beeinflussen.
        with db.engine.connect() as connection:
            return connection.scalar(select(1)) == 1
    except SQLAlchemyError:
        # DB-Ausnahmen können Hostnamen oder Zugangsdaten enthalten.
        return False
