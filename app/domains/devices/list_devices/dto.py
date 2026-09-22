from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    owner_id: int
    offset: int = 0
    limit: int = 20
    # Obere Geräte-ID der Listenansicht, kein Datenbank-Transaktionssnapshot.
    snapshot: int | None = None
    search: str = ""
