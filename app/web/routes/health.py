"""Bereitschaft über die gekapselte technische Schnittstelle."""

from flask import jsonify

from app.diagnostics import check_readiness
from app.web import blueprint


@blueprint.get("/health/ready")
def ready():
    if check_readiness():
        return jsonify(status="ready"), 200
    return jsonify(status="unavailable"), 503
