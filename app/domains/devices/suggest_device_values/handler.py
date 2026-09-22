from app.domains.devices.model import require_owner

from .dto import Query
from .ports import Repository


class SuggestDeviceValues:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, query: Query) -> tuple[str, ...]:
        require_owner(query.owner_id)
        if query.field not in {"name", "manufacturer", "model"}:
            raise ValueError("Unknown device field.")
        for value in (query.term, query.manufacturer):
            if (
                not isinstance(value, str)
                or len(value) > 120
                or any(ord(char) < 32 or ord(char) == 127 for char in value)
            ):
                raise ValueError("Invalid suggestion query.")
        term = query.term.strip()
        if len(term) < 2:
            return ()
        # Modelle sind nur innerhalb des gewählten Herstellers sinnvoll zuzuordnen.
        manufacturer = query.manufacturer.strip() if query.field == "model" else ""
        # Alle Suchteile müssen vorkommen, aber weder als Phrase noch in Eingabereihenfolge.
        terms = tuple(dict.fromkeys(term.lower().split()))
        return self.repository.suggest(query.owner_id, query.field, terms, manufacturer, 10)
