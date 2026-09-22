from typing import Protocol


class Repository(Protocol):
    def delete(self, owner_id: int, parent_id: int, image_id: str) -> bool:
        """Eigentumsgebunden atomar entfernen; False bei fremdem/unbekanntem Bild."""
        ...
