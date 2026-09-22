"""Application Factory für die gemeinsam betriebenen Komponenten."""

from collections.abc import Mapping
from traceback import walk_tb
from typing import Any

from flask import Flask, has_request_context, request
from flask_babel import Babel, get_locale
from flask_babel import gettext as _
from werkzeug.datastructures import LanguageAccept
from werkzeug.exceptions import HTTPException, InternalServerError, SecurityError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import load_config, validate_config
from app.extensions import csrf, db, migrate


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Erzeuge eine unabhängige Instanz ohne Datenbankänderungen beim Start."""
    app = Flask(__name__, static_folder=None, template_folder="web/templates")
    # Den gewählten Modus vor den Overrides anwenden: Sonst könnten z.B.
    # Entwicklungs-Cookie-Defaults in eine Produktionsinstanz übernommen werden.
    app.config.from_mapping(load_config(config.get("REPAIRHUB_ENV") if config else None))
    if config:
        app.config.from_mapping(config)
    validate_config(app.config)

    def select_locale():
        # Sprachpräferenzen stehen in Accept-Language, nicht im User-Agent.
        # Regionale Varianten wie de-CH oder en-GB nutzen ihre Basissprache.
        if not has_request_context():
            return "en"
        # Vor dem Abgleich normalisieren, damit ein exaktes "en" nicht vor
        # einer höher gewichteten regionalen Präferenz wie "de-CH" gewinnt.
        preferences = LanguageAccept(
            [
                (tag.lower().replace("_", "-").split("-", 1)[0], quality)
                for tag, quality in request.accept_languages
            ]
        )
        language = preferences.best_match(("en", "de"))
        return "de_DE" if language == "de" else "en"

    Babel(app, locale_selector=select_locale)

    @app.after_request
    def language_headers(response):
        response.headers["Content-Language"] = str(get_locale()).replace("_", "-")
        # Caches müssen deutsche und englische Antworten getrennt behandeln.
        response.vary.add("Accept-Language")
        if request.path == "/api" or request.path.startswith("/api/"):
            # Auch Routingfehler (404/405) erreichen keinen Blueprint-Hook.
            response.headers["Cache-Control"] = "no-store"
        return response

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    # Nur Nginx erreicht Gunicorn; Nginx überschreibt diese beiden Header.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    from app.adapters.users.identity import FlaskSecurityIdentity
    from app.adapters.users.security import configure_identity
    from app.data.users.model import Role, User
    from app.data.users.security_store import IdentityDatastore

    datastore = IdentityDatastore(db, User, Role)
    security = configure_identity(app, datastore)

    from app.adapters.users.registration import FlaskSecurityUsers
    from app.domains.users.check_reset_link.handler import CheckResetLink
    from app.domains.users.confirm_email.handler import ConfirmEmail
    from app.domains.users.login_user.handler import LoginUser
    from app.domains.users.logout_user.handler import LogoutUser
    from app.domains.users.register_user.handler import RegisterUser
    from app.domains.users.request_password_reset.handler import RequestPasswordReset
    from app.domains.users.resend_confirmation.handler import ResendConfirmation
    from app.domains.users.reset_password.handler import ResetPassword
    from app.web.routes.users import create_user_blueprint

    # Nur die Factory kennt konkrete Adapter und verbindet sie mit den Slice-Ports.
    # Routen erhalten fertige Handler; die Domäne benötigt dadurch keine Flask-Imports.
    gateway = FlaskSecurityUsers(security, datastore)
    app.register_blueprint(
        create_user_blueprint(
            flows={
                "register": RegisterUser(gateway),
                "login": LoginUser(gateway),
                "logout": LogoutUser(gateway),
                "confirm": ConfirmEmail(gateway),
                "resend": ResendConfirmation(gateway),
                "request_reset": RequestPasswordReset(gateway),
                "reset": ResetPassword(gateway),
                "check_reset": CheckResetLink(gateway),
            },
            forms={name: value.cls for name, value in security.forms.items()},
        )
    )
    identity = FlaskSecurityIdentity()
    app.extensions["identity_provider"] = identity

    from app.data.devices.get_device import GetDeviceRepository
    from app.data.devices.list_devices import ListDevicesRepository
    from app.data.devices.register_device import RegisterDeviceRepository
    from app.data.devices.suggest_device_values import SuggestDeviceValuesRepository
    from app.data.devices.update_device import UpdateDeviceRepository
    from app.domains.devices.get_device.handler import GetDevice
    from app.domains.devices.list_devices.handler import ListDevices
    from app.domains.devices.register_device.handler import RegisterDevice
    from app.domains.devices.suggest_device_values.handler import SuggestDeviceValues
    from app.domains.devices.update_device.handler import UpdateDevice
    from app.web.routes.devices import create_device_blueprint

    app.register_blueprint(
        create_device_blueprint(
            identity=identity,
            register=RegisterDevice(RegisterDeviceRepository()),
            update=UpdateDevice(UpdateDeviceRepository()),
            get=GetDevice(GetDeviceRepository()),
            listing=ListDevices(ListDevicesRepository()),
            suggestions=SuggestDeviceValues(SuggestDeviceValuesRepository()),
        )
    )

    from datetime import UTC, datetime

    from app.data.parts.add_part import AddPartRepository
    from app.data.parts.update_part import UpdatePartRepository
    from app.data.repairs.add_step import AddStepRepository
    from app.data.repairs.change_status import ChangeStatusRepository
    from app.data.repairs.create_repair import CreateRepairRepository
    from app.data.repairs.get_repair import GetRepairRepository
    from app.data.repairs.get_status_overview import GetStatusOverviewRepository
    from app.data.repairs.list_repairs import ListRepairsRepository
    from app.data.repairs.update_description import UpdateDescriptionRepository
    from app.data.repairs.update_step import UpdateStepRepository
    from app.data.repairs.update_work import UpdateWorkRepository
    from app.domains.parts.add_part.handler import AddPart
    from app.domains.parts.update_part.handler import UpdatePart
    from app.domains.repairs.add_step.handler import AddStep
    from app.domains.repairs.change_status.handler import ChangeStatus
    from app.domains.repairs.create_repair.handler import CreateRepair
    from app.domains.repairs.get_repair.handler import GetRepair
    from app.domains.repairs.get_status_overview.handler import GetStatusOverview
    from app.domains.repairs.list_repairs.handler import ListRepairs
    from app.domains.repairs.update_description.handler import UpdateDescription
    from app.domains.repairs.update_step.handler import UpdateStep
    from app.domains.repairs.update_work.handler import UpdateWork
    from app.web.routes.repairs import create_repair_blueprint

    app.register_blueprint(
        create_repair_blueprint(
            identity=identity,
            device_reader=GetDevice(GetDeviceRepository()),
            overview=GetStatusOverview(GetStatusOverviewRepository()),
            create=CreateRepair(CreateRepairRepository(), lambda: datetime.now(UTC)),
            listing=ListRepairs(ListRepairsRepository()),
            detail=GetRepair(GetRepairRepository()),
            description=UpdateDescription(UpdateDescriptionRepository()),
            status=ChangeStatus(ChangeStatusRepository()),
            add_step=AddStep(AddStepRepository()),
            update_step=UpdateStep(UpdateStepRepository()),
            work=UpdateWork(UpdateWorkRepository()),
            add_part=AddPart(AddPartRepository()),
            update_part=UpdatePart(UpdatePartRepository()),
        )
    )

    @app.context_processor
    def identity_context():
        # Eigene Vorlagen erhalten nur einen Wert, kein nachladendes ORM-Objekt.
        return {"viewer": identity.current(), "locale": str(get_locale()).replace("_", "-")}

    from app.adapters.users.api_keys import ApiKeys
    from app.api import create_api_blueprint
    from app.domains.users.authenticate_api_key.handler import AuthenticateApiKey
    from app.domains.users.create_api_key.handler import CreateApiKey
    from app.domains.users.get_api_key.handler import GetApiKey
    from app.domains.users.revoke_api_key.handler import RevokeApiKey
    from app.web import blueprint as web_blueprint
    from app.web.routes.api_keys import create_api_key_blueprint

    # Persönliche Keys und System-Key nutzen dieselbe Authentifizierungsgrenze.
    # Die Browserverwaltung erhält weiterhin ausschliesslich kontogebundene Commands.
    keys = ApiKeys(datastore, app.config["API_SMOKE_KEY"])
    app.register_blueprint(web_blueprint)
    app.register_blueprint(
        create_api_key_blueprint(
            identity=identity,
            create=CreateApiKey(keys),
            revoke=RevokeApiKey(keys),
            status=GetApiKey(keys),
        )
    )
    app.register_blueprint(
        create_api_blueprint(
            authenticate=AuthenticateApiKey(keys),
            detail=GetRepair(GetRepairRepository()),
            listing=ListRepairs(ListRepairsRepository()),
        ),
        url_prefix="/api",
    )

    from app.api.errors import render_error as api_error
    from app.web.errors import render_error as web_error

    # Routing-404/405 erreichen noch keinen Blueprint. Auswahl daher hier in der
    # Factory; beide Präsentationskomponenten bleiben voneinander unabhängig.
    # Grundlage: https://flask.palletsprojects.com/en/stable/errorhandling/
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if isinstance(error, SecurityError):
            # Die Hostprüfung kann vor der Erzeugung des URL-Adapters scheitern.
            # Navigation mit url_for würde diese Ablehnung in einen 500er verwandeln.
            response = error.get_response()
            response.set_data(_("Invalid request: untrusted host."))
            response.content_type = "text/plain; charset=utf-8"
            return response
        messages = {
            400: (
                _("Invalid request"),
                _("Please reload the page and check your input."),
            ),
            401: (_("Login required"), _("Please log in to access this resource.")),
            403: (_("Access denied"), _("This action is not allowed.")),
            404: (_("Page not found"), _("The requested resource was not found.")),
            405: (_("Method not allowed"), _("This request method is not supported here.")),
            409: (
                _("Unable to register"),
                _("This username or email address is already in use."),
            ),
            503: (_("Temporarily unavailable"), _("Please try again later.")),
            413: (_("Request too large"), _("The submitted data exceeds the allowed size.")),
            500: (
                _("Internal error"),
                _("The request could not be processed. Please try again later."),
            ),
        }
        title, message = messages.get(
            error.code,
            (
                _("Request failed"),
                _("The request could not be processed."),
            ),
        )
        render = (
            api_error if request.path == "/api" or request.path.startswith("/api/") else web_error
        )
        # Header wie Allow/Retry-After erhalten; niemals Exception-Details ausgeben.
        return render(error.get_response(), title, message)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # Vor Flasks standardmässiger Traceback-Ausgabe abfangen: SQL-/Clientfehler
        # können Zugangsdaten oder Token enthalten. Keine URL/Exception protokollieren.
        locations = " > ".join(
            f"{frame.f_globals.get('__name__', 'unknown')}.{frame.f_code.co_name}:{line}"
            for frame, line in walk_tb(error.__traceback__)
        )
        app.logger.error(
            "Internal application error. Type=%s; Endpoint=%s; Call sites=%s",
            type(error).__name__,
            request.endpoint,
            locations,
        )
        return handle_http_error(InternalServerError())

    return app
