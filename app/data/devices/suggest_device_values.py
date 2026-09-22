"""Keine zweite Stammdatenliste: nur erfolgreich gespeicherte eigene Werte vorschlagen."""

from sqlalchemy import func, select

from app.data.devices.model import Device
from app.extensions import db


class SuggestDeviceValuesRepository:
    def suggest(self, owner_id, field, terms, manufacturer, limit):
        column = {"name": Device.name, "manufacturer": Device.manufacturer, "model": Device.model}[
            field
        ]
        # Eine feste Schreibweise pro Gruppe liefern, ohne private Werte anderer
        # Konten einzubeziehen oder zusätzliche Katalogeinträge zu erzeugen.
        value = func.min(column)
        statement = select(value).where(Device.owner_id == owner_id)
        for term in terms:
            # SQL-Wildcards bleiben Text; jedes Suchteil darf an beliebiger Position stehen.
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(column.ilike(f"%{escaped}%", escape="\\"))
        # Nur Modellvorschläge erhalten vom Anwendungsfall einen Herstellerfilter.
        if manufacturer:
            statement = statement.where(func.lower(Device.manufacturer) == manufacturer.lower())
        statement = statement.group_by(func.lower(column)).order_by(func.lower(column)).limit(limit)
        return tuple(db.session.scalars(statement))
