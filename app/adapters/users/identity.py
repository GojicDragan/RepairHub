"""Flask-Security-Identität in einen frameworkfreien Wert übersetzen."""

from flask_security import current_user

from app.domains.users.dto import UserIdentity


class FlaskSecurityIdentity:
    def current(self) -> UserIdentity | None:
        if not current_user.is_authenticated or current_user.confirmed_at is None:
            return None
        return UserIdentity(current_user.id, current_user.username)
