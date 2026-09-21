"""Framework-Benutzerverwaltung ausserhalb des frameworkfreien Fachkerns."""

from smtplib import SMTPException

from flask import current_app
from flask_babel import lazy_gettext as _
from flask_mailman import Mail
from flask_security import LoginForm, MailUtil, Security
from flask_security.utils import lookup_identity
from werkzeug.exceptions import ServiceUnavailable
from wtforms import StringField
from wtforms.validators import DataRequired, Length


class CombinedLoginForm(LoginForm):
    """Ein gemeinsames Eingabefeld; die Authentifizierung übernimmt Flask-Security."""

    email = None
    identity = StringField(_("Email or username"), validators=[DataRequired(), Length(max=254)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # USERNAME_ENABLE ergänzt das Feld auch bei der Anmeldung. Nur hier
        # ersetzen wir es; die Registrierung erfasst weiterhin beide Angaben.
        del self.username
        # Bibliotheksfehler adressieren email/username als Attribute. Beide
        # verweisen auf dasselbe Feld, ohne zusätzliche Eingaben zu registrieren.
        self.email = self.identity
        self.username = self.identity

    def validate(self, **kwargs):
        self.ifield = self.identity
        self.user = lookup_identity(self.identity.data) if self.identity.data else None
        return super().validate(**kwargs)


class ReliableMailUtil(MailUtil):
    def send_mail(self, *args, **kwargs):
        try:
            return super().send_mail(*args, **kwargs)
        except (OSError, SMTPException):
            # Ein fehlgeschlagener Mailversand darf keine Identitätsänderung
            # speichern. Der Gateway übersetzt diesen Fehler für den Anwendungsfall.
            current_app.extensions["security"].datastore.rollback()
            raise ServiceUnavailable() from None


def configure_identity(app, datastore):
    Mail(app)
    return Security(
        app,
        datastore,
        # Eigene Routen führen zuerst durch die Domänenhandler. Die Formulare und
        # Identitätsverfahren der Bibliothek bleiben dabei weiterhin verfügbar.
        register_blueprint=False,
        mail_util_cls=ReliableMailUtil,
        login_form=CombinedLoginForm,
    )
