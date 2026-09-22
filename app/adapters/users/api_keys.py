"""Zufällige API-Schlüssel; nur Hash und Bindung an die bestätigte Identität speichern."""

import hashlib
import re
import secrets
from datetime import UTC, datetime

from app.domains.users.dto import ApiKeyStatus, GeneratedApiKey, SystemApiIdentity, UserIdentity

KEY_PATTERN = re.compile(r"rh_[A-Za-z0-9_-]{43}\Z")


class ApiKeys:
    def __init__(self, datastore, system_key=""):
        self.datastore = datastore
        if system_key and not KEY_PATTERN.fullmatch(system_key):
            raise ValueError("API_SMOKE_KEY must use rh_ followed by 43 URL-safe characters.")
        # Ein leerer Konfigurationswert deaktiviert nur den Systemzugang.
        # Der Adapter behält vom konfigurierten Schlüssel lediglich den Vergleichshash.
        self.system_digest = self.digest(system_key) if system_key else None

    @staticmethod
    def digest(key):
        # 256 zufällige Bits erlauben SHA-256 statt eines langsamen Passwort-Hashes.
        # Es wird kein vom Benutzer gewähltes Passwort als API-Key akzeptiert.
        return hashlib.sha256(key.encode("ascii")).hexdigest()

    @staticmethod
    def eligible(user):
        return user is not None and user.active and user.confirmed_at is not None

    def _save(self, user, key):
        user.api_key_hash = self.digest(key)
        # Flask-Security ändert diese Identitätskennung beim Passwort-Reset.
        # Dadurch verliert auch ein zuvor ausgestellter API-Key seine Gültigkeit.
        user.api_key_identity = user.fs_uniquifier
        user.api_key_created_at = datetime.now(UTC)
        try:
            self.datastore.commit()
        except Exception:
            self.datastore.rollback()
            raise
        return GeneratedApiKey(key, user.api_key_created_at.isoformat())

    def create(self, command):
        user = self.datastore.find_user(id=command.owner_id)
        if not self.eligible(user):
            return None
        return self._save(user, "rh_" + secrets.token_urlsafe(32))

    def status(self, command):
        user = self.datastore.find_user(id=command.owner_id)
        active = bool(
            self.eligible(user)
            and user.api_key_hash
            and user.api_key_identity == user.fs_uniquifier
        )
        return ApiKeyStatus(active, user.api_key_created_at.isoformat() if active else None)

    def revoke(self, command):
        user = self.datastore.find_user(id=command.owner_id)
        if user is None:
            return
        user.api_key_hash = user.api_key_identity = user.api_key_created_at = None
        try:
            self.datastore.commit()
        except Exception:
            self.datastore.rollback()
            raise

    def authenticate(self, command):
        if not isinstance(command.key, str) or not KEY_PATTERN.fullmatch(command.key):
            return None
        digest = self.digest(command.key)
        # Der Systemzugang gehört keinem Benutzerkonto; seine Leseberechtigung
        # wird erst an der API-Grenze in die Reparaturdomäne übersetzt.
        if self.system_digest and secrets.compare_digest(self.system_digest, digest):
            return SystemApiIdentity()
        user = self.datastore.find_user(api_key_hash=digest)
        if not self.eligible(user) or user.api_key_identity != user.fs_uniquifier:
            return None
        if not secrets.compare_digest(user.api_key_hash, digest):
            return None
        return UserIdentity(user.id, user.username)
