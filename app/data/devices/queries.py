from app.domains.devices.dto import Device


# Werte innerhalb des Datenzugriffs kopieren; ausserhalb darf kein ORM-Objekt
# durch Attributzugriffe weitere Abfragen oder Session-Abhängigkeiten auslösen.
def device_dto(row):
    return Device(row.id, row.name, row.manufacturer, row.model)
