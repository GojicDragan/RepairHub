"""Browser- und AJAX-Adapter; identische Anwendungsfälle und Eigentumsprüfung."""

from dataclasses import asdict

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from werkzeug.exceptions import HTTPException

from app.domains.devices.dto import DeviceValues
from app.domains.devices.errors import DeviceNotFound, InvalidDevice
from app.domains.devices.get_device.dto import Command as Get
from app.domains.devices.list_devices.dto import Command as List
from app.domains.devices.register_device.dto import Command as Register
from app.domains.devices.suggest_device_values.dto import Query as Suggest
from app.domains.devices.update_device.dto import Command as Update
from app.web.forms.devices import DeviceForm


def create_device_blueprint(*, identity, register, update, get, listing, suggestions):
    blueprint = Blueprint("devices", __name__, url_prefix="/devices")

    def wants_json():
        return request.accept_mimetypes.best == "application/json"

    @blueprint.before_request
    def authenticate():
        # Fetch braucht ein erkennbares 401 statt einer HTML-Loginseite mit Status 200.
        if identity.current() is None:
            if wants_json():
                abort(401)
            return redirect(url_for("security.login"))

    @blueprint.after_request
    def private_response(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.vary.add("Accept")
        return response

    @blueprint.errorhandler(HTTPException)
    def http_error(error):
        messages = {
            400: _("Please reload the page and check your input."),
            401: _("Your session has expired. Please log in again."),
            404: _("Device not found."),
        }
        message = messages.get(error.code, _("The request could not be processed."))
        response = error.get_response()
        if wants_json():
            response.data = jsonify(error=message).data
            response.content_type = "application/json"
            return response
        return render_template(
            "error.html", status=error.code, title=_("Request failed"), message=message
        ), error.code

    def owner():
        # Ausschliesslich die geprüfte Sitzung liefert die Eigentümer-ID, niemals der Body.
        return identity.current().id

    def find(device_id):
        try:
            return get.execute(Get(owner(), device_id))
        except DeviceNotFound:
            abort(404)

    @blueprint.get("")
    def index():
        try:
            offset = int(request.args.get("offset", "0"))
            # HTML bleibt bei einer kleinen Startseite; AJAX darf ein grösseres,
            # im Anwendungsfall weiterhin begrenztes Scrollfenster abrufen.
            limit = int(request.args.get("limit", "20")) if wants_json() else 20
            snapshot = request.args.get("snapshot")
            page = listing.execute(
                List(owner(), offset, limit, int(snapshot) if snapshot is not None else None)
            )
        except (ValueError, OverflowError):
            abort(400)
        if wants_json():
            return jsonify(asdict(page))
        return render_template("devices/index.html", page=page)

    @blueprint.get("/suggestions")
    def suggest():
        try:
            items = suggestions.execute(
                Suggest(
                    owner(),
                    request.args.get("field", ""),
                    request.args.get("term", ""),
                    request.args.get("manufacturer", ""),
                )
            )
        except ValueError:
            abort(400)
        return jsonify(items=items)

    @blueprint.get("/<int:device_id>")
    def detail(device_id):
        return render_template("devices/detail.html", device=find(device_id))

    def editor(device_id=None):
        device = find(device_id) if device_id is not None else None
        form = DeviceForm(data=asdict(device) if device else None)
        if request.method == "POST":
            values = request.get_json() if request.is_json else request.form
            if not isinstance(values, dict) and not hasattr(values, "getlist"):
                abort(400)
            # Nur bearbeitbare Felder übernehmen; übermittelte IDs beeinflussen
            # weder Eigentümer noch Zielgerät. CSRF prüft die globale Erweiterung.
            submitted = DeviceValues(
                *(values.get(name, "") for name in ("name", "manufacturer", "model"))
            )
            try:
                saved = (
                    update.execute(Update(owner(), device_id, submitted))
                    if device
                    else register.execute(Register(owner(), submitted))
                )
            except InvalidDevice as error:
                messages = {
                    "required": _("This field is required."),
                    "too_long": _("Use at most 120 characters."),
                    "control_character": _("Use text without control characters."),
                }
                errors = {name: messages[code] for name, code in error.errors.items()}
                if wants_json():
                    return jsonify(errors=errors), 422
                for name, message in errors.items():
                    form[name].errors = [message]
                return render_template("devices/form.html", form=form, device=device), 422
            except DeviceNotFound:
                abort(404)
            message = _("Device saved.")
            if wants_json():
                return jsonify(
                    device=asdict(saved),
                    message=message,
                    url=url_for("devices.detail", device_id=saved.id),
                    edit_url=url_for("devices.edit", device_id=saved.id),
                ), 200 if device else 201
            flash(message)
            return redirect(url_for("devices.detail", device_id=saved.id), code=303)
        return render_template("devices/form.html", form=form, device=device)

    blueprint.add_url_rule("/new", "create", editor, methods=["GET", "POST"])
    blueprint.add_url_rule("/<int:device_id>/edit", "edit", editor, methods=["GET", "POST"])
    return blueprint
