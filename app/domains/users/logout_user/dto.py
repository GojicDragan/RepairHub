from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    # Der Adapter beendet die aktuelle Sitzung; eine vom Client gelieferte Benutzer-ID
    # dürfte nicht bestimmen, wessen Sitzung beendet wird.
    pass
