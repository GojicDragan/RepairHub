"""Dünne HTTP-Adapter; HTML und AJAX verwenden dieselben injizierten Slices."""

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_wtf.csrf import CSRFError
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import HTTPException, Unauthorized
from werkzeug.exceptions import NotFound as HTTPException404

from app.domains.devices.errors import DeviceNotFound
from app.domains.devices.get_device.dto import Command as DeviceQuery
from app.domains.parts.add_part.dto import Command as AddPart
from app.domains.parts.errors import InvalidPart, PartNotFound
from app.domains.parts.update_part.dto import Command as UpdatePart
from app.domains.repairs.add_step.dto import Command as AddStep
from app.domains.repairs.change_status.dto import Command as ChangeStatus
from app.domains.repairs.create_repair.dto import Command as Create
from app.domains.repairs.errors import InvalidRepair, RepairNotFound
from app.domains.repairs.get_repair.dto import Command as Get
from app.domains.repairs.list_repairs.dto import Command as List
from app.domains.repairs.update_description.dto import Command as Description
from app.domains.repairs.update_step.dto import Command as UpdateStep
from app.domains.repairs.update_work.dto import Command as Work
from app.web.forms.repairs import DescriptionForm, PartForm, StatusForm, StepForm, WorkForm


def create_repair_blueprint(
    *,
    identity,
    device_reader,
    create,
    listing,
    detail,
    description,
    status,
    add_step,
    update_step,
    work,
    add_part,
    update_part,
):
    blueprint = Blueprint("repairs", __name__)

    def wants_json():
        return request.accept_mimetypes.best == "application/json"

    def owner():
        return identity.current().id

    @blueprint.before_request
    def authenticate():
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

    @blueprint.errorhandler(PartNotFound)
    @blueprint.errorhandler(RepairNotFound)
    @blueprint.errorhandler(DeviceNotFound)
    def not_found(error):
        return http_error(HTTPException404())

    @blueprint.errorhandler(HTTPException)
    def http_error(error):
        # Eine abgelaufene Sitzung verliert auch ihren CSRF-Wert. Der Schreibzugriff
        # bleibt abgewiesen; Fetch benötigt hier den Anmeldehinweis statt eines 400.
        if isinstance(error, CSRFError) and wants_json() and identity.current() is None:
            error = Unauthorized()
        message = {
            401: _("Your session has expired. Please log in again."),
            404: _("Repair not found."),
        }.get(error.code, _("Please reload the page and check your input."))
        if wants_json():
            return jsonify(error=message), error.code
        return render_template(
            "error.html", status=error.code, title=_("Request failed"), message=message
        ), error.code

    def get_offset():
        try:
            return int(request.args.get("offset", "0"))
        except (ValueError, OverflowError):
            abort(400)

    def load(repair_id, offset=None):
        try:
            return detail.execute(
                Get(
                    owner(),
                    repair_id,
                    get_offset() if offset is None else offset,
                    int(request.args.get("part_offset", "0")),
                )
            )
        except ValueError:
            abort(400)

    def labels():
        return {"open": _("Open"), "in_progress": _("In progress"), "completed": _("Completed")}

    def workspace(data, invalid=None):
        # Mehrere unabhängige Formulare teilen sich einen Request. Ohne formdata=None
        # würde WTForms dessen POST-Daten auch in unbeteiligte Formulare übernehmen.
        forms = {
            "description": DescriptionForm(
                formdata=None, data={"description": data.repair.description}
            ),
            "status": StatusForm(formdata=None, data={"status": data.repair.status}),
            "new-step": StepForm(formdata=None),
            "work": WorkForm(
                formdata=None,
                data={
                    "hours": format(data.hours, ".2f"),
                    "hourly_rate": format(data.hourly_rate, ".2f"),
                },
            ),
            "new-part": PartForm(formdata=None, data={"quantity": "1"}),
            **{
                f"part-{part.id}": PartForm(
                    formdata=None,
                    data={
                        "name": part.name,
                        "unit_price": format(part.unit_price, ".2f"),
                        "quantity": str(part.quantity),
                    },
                )
                for part in data.parts
            },
            **{
                f"step-{step.id}": StepForm(
                    formdata=None,
                    data={"description": step.description, "completed": step.completed},
                )
                for step in data.steps
            },
        }
        if invalid:
            key, submitted, errors = invalid
            form = forms.get(key)
            if form:
                form.process(formdata=MultiDict(submitted))
                for field, message in errors.items():
                    form[field].errors = [message]
        return render_template(
            "repairs/_detail.html", data=data, forms=forms, status_labels=labels()
        )

    def page(content, title):
        return render_template("repairs/page.html", content=content, title=title)

    def values():
        submitted = request.get_json() if request.is_json else request.form
        if not isinstance(submitted, dict) and not isinstance(submitted, MultiDict):
            abort(400)
        return submitted

    def errors_for(error, maximum):
        messages = {
            "required": _("This field is required."),
            "too_long": _("Use at most %(count)s characters.", count=maximum),
            "control_character": _("Use text without control characters."),
            "invalid_status": _("Choose a valid repair status."),
            "invalid_completed": _("Choose a valid completion state."),
            "invalid_decimal": _(
                "Enter a nonnegative amount with at most two decimal places "
                "within the displayed limit."
            ),
            "invalid_quantity": _("Enter a whole quantity between 1 and 2147483647."),
            "invalid_name": _("Use at most 200 characters without control characters."),
        }
        return {field: messages[code] for field, code in error.errors.items()}

    @blueprint.get("/repairs")
    def index():
        try:
            device_id = int(request.args["device_id"]) if "device_id" in request.args else None
            snapshot = request.args.get("snapshot")
            result = listing.execute(
                List(
                    owner(),
                    device_id,
                    get_offset(),
                    int(request.args.get("limit", "20")) if wants_json() else 20,
                    int(snapshot) if snapshot is not None else None,
                )
            )
        except (ValueError, OverflowError):
            abort(400)
        if wants_json():
            status_labels = labels()
            return jsonify(
                offset=result.offset,
                total=result.total,
                snapshot=result.snapshot,
                items=[
                    dict(
                        id=item.id,
                        device_name=item.device_name,
                        description=item.description,
                        status=item.status,
                        status_label=status_labels[item.status],
                        label=_("Repair #%(id)s", id=item.id),
                        url=url_for(
                            "repairs.show",
                            repair_id=item.id,
                            **({"device_id": device_id} if device_id else {}),
                        ),
                    )
                    for item in result.items
                ],
            )
        return render_template(
            "repairs/index.html", page=result, device_id=device_id, status_labels=labels()
        )

    @blueprint.route("/devices/<int:device_id>/repairs/new", methods=["GET", "POST"])
    def new(device_id):
        device = device_reader.execute(DeviceQuery(owner(), device_id))
        form = DescriptionForm()
        if request.method == "POST":
            submitted = values()
            try:
                repair = create.execute(
                    Create(owner(), device_id, submitted.get("description", ""))
                )
            except InvalidRepair as error:
                errors = errors_for(error, 10000)
                if wants_json():
                    return jsonify(errors=errors), 422
                form.description.errors = [errors["description"]]
                return page(
                    render_template("repairs/_new.html", device=device, form=form), _("New repair")
                ), 422
            return saved(repair.id)
        return page(render_template("repairs/_new.html", device=device, form=form), _("New repair"))

    @blueprint.get("/repairs/<int:repair_id>")
    def show(repair_id):
        return page(workspace(load(repair_id)), _("Repair details"))

    def saved(repair_id, *, show_last_step=False, show_last_part=False):
        data = load(repair_id)
        # Schritte sind aufsteigend sortiert; nach dem Anlegen die Seite des
        # neuen Schritts anzeigen statt auf der bisherigen Seite zu bleiben.
        if show_last_step:
            data = load(repair_id, max(0, ((data.step_total - 1) // 20) * 20))
        if show_last_part:
            data = detail.execute(
                Get(
                    owner(), repair_id, data.step_offset, max(0, ((data.part_total - 1) // 20) * 20)
                )
            )
        target = url_for(
            "repairs.show",
            repair_id=repair_id,
            **({"offset": data.step_offset} if data.step_offset else {}),
            **({"part_offset": data.part_offset} if data.part_offset else {}),
            **(
                {"device_id": data.repair.device_id}
                if request.args.get("device_id") == str(data.repair.device_id)
                else {}
            ),
        )
        if wants_json():
            return jsonify(
                html=workspace(data),
                url=target,
                message=_("Repair saved."),
                title=_("Repair details") + " | RepairHub",
            )
        flash(_("Repair saved."))
        return redirect(target, code=303)

    def mutate(repair_id, kind, step_id=None):
        # Vor Validierung und Rendering stets die eigene Fallzuordnung nachweisen.
        data = load(repair_id)
        submitted = values()
        text = submitted.get("description", "")
        done = submitted.get("completed", False)
        # HTML liefert Checkboxwerte als Text, JSON als bool. Unbekannte Werte
        # bleiben unverändert, damit die Domäne sie statt einer Wahrheitskonvertierung ablehnt.
        if not request.is_json:
            done = {"true": True, "false": False, False: False}.get(done, done)
        commands = {
            "description": (description, Description(owner(), repair_id, text)),
            "status": (status, ChangeStatus(owner(), repair_id, submitted.get("status", ""))),
            "new-step": (add_step, AddStep(owner(), repair_id, text)),
            "step": (update_step, UpdateStep(owner(), repair_id, step_id, text, done)),
        }
        handler, command = commands[kind]
        try:
            handler.execute(command)
        except InvalidRepair as error:
            errors = errors_for(error, 2000 if kind in {"new-step", "step"} else 10000)
            if wants_json():
                return jsonify(errors=errors), 422
            key = f"step-{step_id}" if kind == "step" else kind
            return page(workspace(data, (key, submitted, errors)), _("Repair details")), 422
        return saved(repair_id, show_last_step=kind == "new-step")

    @blueprint.post("/repairs/<int:repair_id>/description")
    def edit_description(repair_id):
        return mutate(repair_id, "description")

    @blueprint.post("/repairs/<int:repair_id>/status")
    def change_status(repair_id):
        return mutate(repair_id, "status")

    @blueprint.post("/repairs/<int:repair_id>/steps")
    def create_step(repair_id):
        return mutate(repair_id, "new-step")

    @blueprint.post("/repairs/<int:repair_id>/steps/<int:step_id>")
    def edit_step(repair_id, step_id):
        return mutate(repair_id, "step", step_id)

    def mutate_costs(repair_id, kind, part_id=None):
        data = load(repair_id)
        submitted = values()
        try:
            if kind == "work":
                work.execute(
                    Work(
                        owner(),
                        repair_id,
                        submitted.get("hours", ""),
                        submitted.get("hourly_rate", ""),
                    )
                )
            elif kind == "new-part":
                add_part.execute(
                    AddPart(
                        owner(),
                        repair_id,
                        submitted.get("name", ""),
                        submitted.get("unit_price", ""),
                        submitted.get("quantity", ""),
                    )
                )
            else:
                update_part.execute(
                    UpdatePart(
                        owner(),
                        repair_id,
                        part_id,
                        submitted.get("name", ""),
                        submitted.get("unit_price", ""),
                        submitted.get("quantity", ""),
                    )
                )
        except (InvalidRepair, InvalidPart) as error:
            errors = errors_for(error, 200)
            if wants_json():
                return jsonify(errors=errors), 422
            key = f"part-{part_id}" if kind == "part" else kind
            return page(workspace(data, (key, submitted, errors)), _("Repair details")), 422
        return saved(repair_id, show_last_part=kind == "new-part")

    @blueprint.post("/repairs/<int:repair_id>/work")
    def edit_work(repair_id):
        return mutate_costs(repair_id, "work")

    @blueprint.post("/repairs/<int:repair_id>/parts")
    def create_part(repair_id):
        return mutate_costs(repair_id, "new-part")

    @blueprint.post("/repairs/<int:repair_id>/parts/<int:part_id>")
    def edit_part(repair_id, part_id):
        return mutate_costs(repair_id, "part", part_id)

    return blueprint
