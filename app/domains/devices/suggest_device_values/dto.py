from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    owner_id: int
    field: str
    term: str
    manufacturer: str = ""
