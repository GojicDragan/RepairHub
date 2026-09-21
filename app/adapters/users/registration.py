"""Flask-Security-Funktionen hinter den frameworkfreien Ports der Benutzerdomäne.

Verwendet die APIs für Registrierung, Bestätigung und Passwortwiederherstellung,
nicht die HTTP-Views der Bibliothek. Integrationsgrenze: docs/user-use-cases.md.
"""

from dataclasses import asdict

from flask_security import login_user, logout_user
from flask_security.confirmable import (
    confirm_email_token_status,
    confirm_user,
    send_confirmation_instructions,
)
from flask_security.forms import form_errors_munge
from flask_security.recoverable import (
    reset_password_token_status,
    send_reset_password_instructions,
    update_password,
)
from flask_security.registerable import register_existing, register_user
from flask_security.utils import hash_password
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import Conflict, ServiceUnavailable

from app.domains.users.check_reset_link.dto import Command as CheckResetLinkCommand
from app.domains.users.confirm_email.dto import Command as ConfirmEmailCommand
from app.domains.users.dto import UserResult
from app.domains.users.login_user.dto import Command as LoginUserCommand
from app.domains.users.logout_user.dto import Command as LogoutUserCommand
from app.domains.users.register_user.dto import Command as RegisterUserCommand
from app.domains.users.request_password_reset.dto import Command as RequestPasswordResetCommand
from app.domains.users.resend_confirmation.dto import Command as ResendConfirmationCommand
from app.domains.users.reset_password.dto import Command as ResetPasswordCommand


class FlaskSecurityUsers:
    def __init__(self, security, datastore):
        self.security = security
        self.datastore = datastore

    def _form(self, name, command):
        # Die Webschicht prüft CSRF. Die Bibliotheksvalidierung erhält hier nur
        # die übergebenen Command-Daten und liest nicht implizit request.form.
        form = self.security.forms[name].cls(
            formdata=MultiDict(asdict(command)), meta={"csrf": False}
        )
        # NextFormMixin liest beim Erzeugen Queryparameter. Weiterleitungen
        # gehören jedoch zur Webschicht und nicht zum Identitätsauftrag.
        if hasattr(form, "next"):
            form.next.data = ""
        return form

    @staticmethod
    def _errors(form):
        return UserResult(
            "invalid",
            tuple(
                (name, tuple(str(message) for message in messages))
                for name, messages in form.errors.items()
            ),
        )

    def _transaction(self, operation):
        # Die Datenbank wird erst nach erfolgreicher Operation bestätigt. Bereits
        # versendete E-Mails lassen sich durch ein DB-Rollback jedoch nicht zurücknehmen.
        try:
            result = operation()
            self.datastore.commit()
            return result
        except Conflict:
            self.datastore.rollback()
            return UserResult("conflict")
        except ServiceUnavailable:
            self.datastore.rollback()
            return UserResult("unavailable")
        except Exception:
            self.datastore.rollback()
            raise

    def register(self, command: RegisterUserCommand) -> UserResult:
        def operation():
            form = self._form("register_form", command)
            if form.validate():
                register_user(form)
                return UserResult()
            # Bereits registrierte Konten durch den Bibliotheksablauf behandeln,
            # ohne über unterschiedliche Erfolgsantworten ihre Existenz preiszugeben.
            if register_existing(form):
                return UserResult()
            return self._errors(form)

        return self._transaction(operation)

    def login(self, command: LoginUserCommand) -> UserResult:
        form = self._form("login_form", command)
        if not form.validate():
            form_errors_munge(
                form,
                {
                    "email": {"replace_msg": "GENERIC_AUTHN_FAILED"},
                    "password": {"replace_msg": "GENERIC_AUTHN_FAILED"},
                },
            )
            self.datastore.rollback()
            return self._errors(form)
        # Ein mögliches Hash-Upgrade der Bibliothek vor dem Sitzungsbeginn speichern.
        try:
            self.datastore.commit()
        except Exception:
            self.datastore.rollback()
            raise
        login_user(form.user, remember=command.remember, authn_via=["password"])
        return UserResult()

    def logout(self, command: LogoutUserCommand) -> UserResult:
        logout_user()
        return UserResult()

    def confirm(self, command: ConfirmEmailCommand) -> UserResult:
        def operation():
            expired, invalid, user = confirm_email_token_status(command.token)
            if expired or invalid or user is None:
                return UserResult("invalid_token")
            if not confirm_user(user):
                return UserResult("already_confirmed")
            logout_user()
            return UserResult()

        return self._transaction(operation)

    def _send(self, name, command, send):
        def operation():
            form = self._form(name, command)
            if form.validate():
                send(form.user)
            else:
                # Einheitliche Antworten und Laufzeitausgleich erschweren die Kontenermittlung.
                hash_password("not-a-password")
            return UserResult()

        return self._transaction(operation)

    def resend(self, command: ResendConfirmationCommand) -> UserResult:
        return self._send("send_confirmation_form", command, send_confirmation_instructions)

    def request_reset(self, command: RequestPasswordResetCommand) -> UserResult:
        return self._send("forgot_password_form", command, send_reset_password_instructions)

    def check_reset(self, command: CheckResetLinkCommand) -> UserResult:
        expired, invalid, user = reset_password_token_status(command.token)
        return UserResult("invalid_token" if expired or invalid or user is None else "ok")

    def reset(self, command: ResetPasswordCommand) -> UserResult:
        def operation():
            # Beim POST erneut prüfen: Ein vorheriger GET autorisiert keine Änderung.
            expired, invalid, user = reset_password_token_status(command.token)
            if expired or invalid or user is None:
                return UserResult("invalid_token")
            form = self._form("reset_password_form", command)
            form.user = user
            if not form.validate():
                return self._errors(form)
            update_password(user, form.password.data)
            return UserResult()

        return self._transaction(operation)
