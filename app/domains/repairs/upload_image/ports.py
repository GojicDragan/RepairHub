from collections.abc import Callable
from typing import Protocol

from app.domains.repairs.dto import Image


class Repository(Protocol):
    def owns(self, owner_id: int, parent_id: int) -> bool: ...
    def add(self, owner_id: int, parent_id: int, image: Image) -> None: ...


class Processor(Protocol):
    def prepare(self, content: bytes) -> tuple[bytes, bytes, int, int]:
        """Dekodieren und bereinigen; ValueError bei ungültigen Bilddaten."""
        ...


class Storage(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> None:
        """OSError bei nicht sicher abgeschlossenem Speichern."""
        ...


KeyFactory = Callable[[], str]
