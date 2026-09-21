"""Application Factory für die gemeinsam betriebenen Komponenten."""

from collections.abc import Mapping
from typing import Any

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import load_config, validate_config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Erzeuge eine unabhängige Instanz ohne Datenbankänderungen beim Start."""
    app = Flask(__name__, static_folder=None)
    app.config.from_mapping(load_config())
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
    return app
