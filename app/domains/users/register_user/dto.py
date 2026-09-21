from dataclasses import dataclass, field


@dataclass(frozen=True)
class Command:
    username: str
    email: str
    # repr=False verhindert Passwörter in der automatisch erzeugten Objektdarstellung.
    # Der Klartext bleibt für die Übergabe an den Identitätsanbieter im Speicher nötig.
    password: str = field(repr=False)
    password_confirm: str = field(repr=False)
