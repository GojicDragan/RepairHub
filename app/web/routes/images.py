"""Gemeinsamer HTTP-Adapter; fachliche Eigentumsprüfung bleibt in den injizierten Slices."""

from io import BytesIO

from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_babel import gettext as _
from werkzeug.exceptions import HTTPException

from app.domains.devices.errors import ImageNotFound as DeviceImageNotFound
from app.domains.devices.errors import ImageUnavailable as DeviceImageUnavailable
from app.domains.devices.errors import InvalidImage as InvalidDeviceImage
from app.domains.repairs.errors import ImageNotFound as RepairImageNotFound
from app.domains.repairs.errors import ImageUnavailable as RepairImageUnavailable
from app.domains.repairs.errors import InvalidImage as InvalidRepairImage


def create_image_blueprint(
    *,
    name,
    prefix,
    identity,
    upload,
    listing,
    get,
    delete,
    delete_command,
    upload_command,
    list_command,
    get_command,
    detail_endpoint,
    parent_arg,
):
    blueprint = Blueprint(name, __name__, url_prefix=prefix)

    def json_request():
        return request.accept_mimetypes.best == "application/json"

    def detail_url(parent_id):
        return url_for(detail_endpoint, **{parent_arg: parent_id}, _anchor="images")

    def render_gallery(parent_id, error="", offset=None):
        try:
            page = listing.execute(
                list_command(
                    identity.current().id,
                    parent_id,
                    int(request.args.get("image_offset", "0")) if offset is None else offset,
                )
            )
        except ValueError:
            abort(400)
        return render_template(
            "images/_gallery.html",
            page=page,
            parent_id=parent_id,
            images_endpoint=name,
            error=error,
        )

    @blueprint.before_request
    def authenticate():
        if identity.current() is None:
            if json_request() or request.endpoint == name + ".content":
                abort(401)
            return redirect(url_for("security.login"))

    @blueprint.after_request
    def private(response):
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.vary.add("Accept")
        return response

    @blueprint.errorhandler(DeviceImageNotFound)
    @blueprint.errorhandler(RepairImageNotFound)
    def missing(error):
        return http_error(HTTPException404())

    @blueprint.errorhandler(DeviceImageUnavailable)
    @blueprint.errorhandler(RepairImageUnavailable)
    def unavailable(error):
        return failure(_("Image storage is currently unavailable. Please try again."), 503)

    def failure(message, status):
        if json_request():
            return jsonify(error=message), status
        return render_template(
            "error.html", title=_("Request failed"), message=message, status=status
        ), status

    @blueprint.errorhandler(HTTPException)
    def http_error(error):
        messages = {
            401: _("Your session has expired. Please log in again."),
            404: _("Image not found."),
            413: _("Choose an image of at most 10 MiB."),
        }
        return failure(
            messages.get(error.code, _("Please reload the page and check your input.")),
            error.code or 500,
        )

    # Import nur für den HTTP-Status; kein technischer Fehler wird an Benutzer durchgereicht.
    from werkzeug.exceptions import NotFound as HTTPException404

    @blueprint.route("", methods=["GET", "POST"])
    def gallery(parent_id):
        error = ""
        code = 200
        if request.method == "POST":
            file = request.files.get("image")
            try:
                upload.execute(
                    upload_command(
                        identity.current().id,
                        parent_id,
                        file.filename if file else "",
                        file.stream.read(10 * 1024 * 1024 + 1) if file else b"",
                    )
                )
            except (InvalidDeviceImage, InvalidRepairImage):
                error = _(
                    "Choose a valid, non-animated JPEG, PNG or WebP image: "
                    "at most 10 MiB and 20 megapixels."
                )
                code = 422
            else:
                if not json_request():
                    return redirect(detail_url(parent_id), code=303)
                # Neue Bilder stehen zuerst; nicht auf einem alten Seitenoffset verbleiben.
                return jsonify(
                    html=render_gallery(parent_id, offset=0), message=_("Image uploaded.")
                ), 201
        html = render_gallery(parent_id, error)
        if json_request():
            return jsonify(html=html, error=error), code
        return render_template(
            "images/page.html", gallery=html, back_url=detail_url(parent_id)
        ), code

    @blueprint.post("/<image_id>/delete")
    def remove(parent_id, image_id):
        # Erst nach erfolgreichem Commit neu rendern; ein Fehler bleibt für den Client sichtbar.
        delete.execute(delete_command(identity.current().id, parent_id, image_id))
        if json_request():
            return jsonify(html=render_gallery(parent_id, offset=0), message=_("Image deleted."))
        return redirect(detail_url(parent_id), code=303)

    @blueprint.get("/<image_id>")
    def content(parent_id, image_id):
        content = get.execute(
            get_command(
                identity.current().id, parent_id, image_id, request.args.get("thumbnail") == "1"
            )
        )
        # Keine Weiterleitung auf öffentliche oder signierte S3-URLs: Jeder Abruf
        # prüft die aktuelle Sitzung und das Eigentum erneut.
        return send_file(
            BytesIO(content),
            mimetype="image/webp",
            download_name=f"image-{image_id}.webp",
            conditional=False,
            etag=False,
            max_age=0,
        )

    return blueprint, render_gallery
