from typing import Protocol


class Repository(Protocol):
    def suggest(
        self, owner_id: int, field: str, terms: tuple[str, ...], manufacturer: str, limit: int
    ) -> tuple[str, ...]: ...
