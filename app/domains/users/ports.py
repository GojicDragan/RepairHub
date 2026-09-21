"""Vertrag zur Identitätsermittlung, ohne Sitzung, Flask oder ORM."""

from typing import Protocol

from .dto import UserIdentity


class IdentityProvider(Protocol):
    def current(self) -> UserIdentity | None:
        """Nur angemeldete, bestätigte Benutzer liefern; sonst None."""
        ...
