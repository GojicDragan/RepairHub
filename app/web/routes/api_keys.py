"""API-Key-Verwaltung mit Sitzung und CSRF; Schlüssel nie in Flash oder Session speichern."""

from flask import Blueprint, abort, redirect, render_template, url_for

from app.domains.users.create_api_key.dto import Command as Create
from app.domains.users.get_api_key.dto import Command as Get
from app.domains.users.revoke_api_key.dto import Command as Revoke


def create_api_key_blueprint(*, identity, create, revoke, status):
    blueprint = Blueprint("api_keys", __name__, url_prefix="/account/api-key")

    @blueprint.before_request
    def authenticate():
        if identity.current() is None:
            return redirect(url_for("security.login"))

    @blueprint.after_request
    def private(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @blueprint.get("")
    def index():
        return render_template(
            "users/api_key.html",
            key_status=status.execute(Get(identity.current().id)),
            generated=None,
        )

    @blueprint.post("")
    def generate():
        generated = create.execute(Create(identity.current().id))
        if generated is None:
            abort(403)
        # Nur diese POST-Antwort enthält den Klartext. Ein erneuter GET kann ihn
        # nicht wiederherstellen; Ersetzen macht den vorherigen Schlüssel ungültig.
        return render_template(
            "users/api_key.html",
            key_status=status.execute(Get(identity.current().id)),
            generated=generated,
        )

    @blueprint.post("/revoke")
    def remove():
        revoke.execute(Revoke(identity.current().id))
        return redirect(url_for("api_keys.index"), code=303)

    return blueprint
