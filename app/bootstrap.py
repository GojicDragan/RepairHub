"""Application Factory für die gemeinsam betriebenen Komponenten."""

from collections.abc import Mapping
from traceback import walk_tb
from typing import Any

from flask import Flask, request
from werkzeug.exceptions import HTTPException, InternalServerError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import load_config, validate_config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Erzeuge eine unabhängige Instanz ohne Datenbankänderungen beim Start."""
    app = Flask(__name__, static_folder=None)
    # Den gewählten Modus vor den Overrides anwenden: Sonst könnten z.B.
    # Entwicklungs-Cookie-Defaults in eine Produktionsinstanz übernommen werden.
    app.config.from_mapping(load_config(config.get("REPAIRHUB_ENV") if config else None))
    if config:
        app.config.from_mapping(config)
    validate_config(app.config)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    # Benutzer-Lader und current_user-Kontext werden gemeinsam in T05 ergänzt.
    login_manager.init_app(app, add_context_processor=False)

    # Nur Nginx erreicht Gunicorn; Nginx überschreibt diese beiden Header.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    from app.api import blueprint as api_blueprint
    from app.web import blueprint as web_blueprint

    app.register_blueprint(web_blueprint)
    app.register_blueprint(api_blueprint, url_prefix="/api")

    from app.api.errors import render_error as api_error
    from app.web.errors import render_error as web_error

    # Routing-404/405 erreichen noch keinen Blueprint. Auswahl daher hier in der
    # Factory; beide Präsentationskomponenten bleiben voneinander unabhängig.
    # Grundlage: https://flask.palletsprojects.com/en/stable/errorhandling/
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        messages = {
            400: (
                "Ungültige Anfrage",
                "Bitte laden Sie die Seite neu und prüfen Sie Ihre Eingaben.",
            ),
            401: ("Anmeldung erforderlich", "Für diesen Zugriff müssen Sie sich anmelden."),
            403: ("Zugriff nicht erlaubt", "Diese Aktion ist nicht erlaubt."),
            404: ("Seite nicht gefunden", "Die angeforderte Ressource wurde nicht gefunden."),
            405: ("Methode nicht erlaubt", "Diese Anfrageart wird hier nicht unterstützt."),
            413: ("Anfrage zu gross", "Die übermittelten Daten überschreiten die erlaubte Grösse."),
            500: (
                "Interner Fehler",
                "Die Anfrage konnte nicht verarbeitet werden. "
                "Bitte versuchen Sie es später erneut.",
            ),
        }
        title, message = messages.get(
            error.code,
            (
                "Anfrage fehlgeschlagen",
                "Die Anfrage konnte nicht verarbeitet werden.",
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
            "Interner Anwendungsfehler. Typ=%s; Endpoint=%s; Aufrufstellen=%s",
            type(error).__name__,
            request.endpoint,
            locations,
        )
        return handle_http_error(InternalServerError())

    return app
