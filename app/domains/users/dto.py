"""Frameworkfreie Identität und Ergebnisse für die Grenzen der Benutzeranwendungsfälle."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserIdentity:
    id: int
    username: str


@dataclass(frozen=True)
class UserResult:
    """Keine Formulare, HTTP-Antworten oder ORM-Objekte über die Anwendungsgrenze geben.

    Der Bibliotheksadapter übersetzt Meldungen bereits. Stabile Codes steuern
    die Darstellung; Feldfehler enthalten nur unveränderliche Meldungstexte.
    """

    code: str = "ok"
    errors: tuple[tuple[str, tuple[str, ...]], ...] = ()
