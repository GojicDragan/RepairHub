"""Flask-Security-Datastore mit atomarer Konfliktbehandlung."""

from flask_security import SQLAlchemyUserDatastore
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Conflict


class IdentityDatastore(SQLAlchemyUserDatastore):
    def rollback(self):
        self.db.session.rollback()

    def create_user(self, **kwargs):
        try:
            user = super().create_user(**kwargs)
            # Konflikte vor Mailversand und Anmeldung erkennen. Die Vorabprüfung
            # im Standardformular allein verhindert keine konkurrierenden INSERTs.
            self.db.session.flush()
            return user
        except IntegrityError as error:
            self.rollback()
            if getattr(error.orig, "sqlstate", None) == "23505" and getattr(
                getattr(error.orig, "diag", None), "constraint_name", None
            ) in {"uq_users_username", "uq_users_email"}:
                raise Conflict() from None
            raise
