from collections.abc import Mapping
from typing import Protocol


class Repository(Protocol):
    def count_by_status(self, owner_id: int) -> Mapping[str, int]: ...
