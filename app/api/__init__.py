"""Lesende API: Persönliche Schlüssel oder expliziter System-Lesezugang."""

from flask import Blueprint, abort, jsonify, request
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.exceptions import Unauthorized

from app.domains.repairs.dto import SystemReadAccess
from app.domains.repairs.errors import RepairNotFound
from app.domains.repairs.get_repair.dto import Command as RepairCommand
from app.domains.repairs.list_repairs.dto import Command as ListCommand
from app.domains.users.authenticate_api_key.dto import Command as Authenticate
from app.domains.users.dto import SystemApiIdentity

from .schemas import repair_document, repair_summary


def create_api_blueprint(*, authenticate, detail, listing):
    blueprint = Blueprint("api", __name__)

    def owner():
        # Browsersitzungen und Queryparameter autorisieren die API nicht.
        # Bearer bezeichnet hier einen opaken Schlüssel, kein JWT-Format.
        authorization = request.headers.get("Authorization", "").split()
        identity = None
        if len(authorization) == 2 and authorization[0].lower() == "bearer":
            identity = authenticate.execute(Authenticate(authorization[1]))
        if identity is None:
            raise Unauthorized(www_authenticate=WWWAuthenticate("bearer", {"realm": "RepairHub"}))
        # Nur das Ergebnis der Schlüsselprüfung darf systemweiten Zugriff erteilen;
        # weder eine übermittelte Benutzer-ID noch ein fehlender Eigentümer genügt.
        return (
            SystemReadAccess.ALL_REPAIRS if isinstance(identity, SystemApiIdentity) else identity.id
        )

    def integer(name, default, maximum):
        values = request.args.getlist(name)
        if not values:
            return default
        # Mehrdeutige Parameter und überlange Zahlen vor der Konvertierung abweisen;
        # die Obergrenze passt zum BIGINT-Bereich der Datenbank.
        if (
            len(values) != 1
            or not values[0].isascii()
            or not values[0].isdecimal()
            or len(values[0]) > 19
        ):
            abort(400)
        value = int(values[0])
        if value > maximum:
            abort(400)
        return value

    @blueprint.get("/repairs")
    def repairs():
        owner_id = owner()
        limit = integer("limit", 20, 60)
        if limit == 0:
            abort(400)
        offset = integer("offset", 0, 9223372036854775807)
        snapshot = integer("snapshot", None, 9223372036854775807)
        result = listing.execute(
            ListCommand(owner_id, offset=offset, limit=limit, snapshot=snapshot)
        )
        next_offset = offset + len(result.items)
        return jsonify(
            items=[repair_summary(item) for item in result.items],
            total=result.total,
            offset=offset,
            limit=limit,
            snapshot=result.snapshot,
            next_offset=next_offset if next_offset < result.total else None,
        )

    @blueprint.get("/repairs/<int:repair_id>")
    def repair(repair_id):
        owner_id = owner()
        try:
            result = detail.execute(RepairCommand(owner_id, repair_id, complete=True))
        except RepairNotFound:
            abort(404)
        return jsonify(repair_document(result))

    return blueprint
