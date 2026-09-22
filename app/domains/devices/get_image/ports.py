from typing import Protocol

from app.domains.devices.dto import Image


class Repository(Protocol):
    def get(self, owner_id: int, parent_id: int, image_id: str) -> Image | None: ...


class Storage(Protocol):
    def read(self, key: str) -> bytes:
        """OSError bei fehlendem Objekt oder nicht verfügbarem Speicher."""
        ...
