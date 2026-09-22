"""Positive und negative Beispiele schützen die tatsächlichen Modulgrenzen."""

from pathlib import Path

import pytest

from scripts.check_architecture import check_project, check_source

ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
)


def test_project_matches_component_contract():
    assert check_project(ROOT) == []


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("app.web.routes.repairs", "from app.domains.repairs import get_repair"),
        ("app.api.routes", "from app.domains.users import authenticate_api_key"),
        ("app.domains.repairs", "from app.domains.costs import calculate"),
        ("app.data.queries", "from app.domains.parts.ports import PartRepository"),
        ("app.data.queries", "from app.domains.parts.dto import PartSnapshot"),
        ("app.domains.costs", "from decimal import Decimal"),
        ("app.web.routes.health", "from app.diagnostics import check_readiness"),
        ("app.data.health", "from app.extensions import db"),
    ],
)
def test_allowed_dependencies(module, source):
    assert check_source(source, module) == []


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("app.web.routes.repairs", "from app.data.models import Repair"),
        ("app.web.routes.repairs", "from app import data"),
        ("app.web.routes.repairs", "from ...data import models"),
        ("app.api.routes", "from app.domains.parts import get_part"),
        ("app.api.routes", "import app.domains.devices as devices"),
        ("app.domains.parts", "from app.domains.repairs import get_repair"),
        ("app.domains.costs", "from ..data import queries"),
        ("app.domains.costs", "from flask import current_app"),
        ("app.domains.costs", "import sqlalchemy"),
        ("app.web.routes.repairs", "from app.extensions import db as store"),
        ("app.web.routes.repairs", "import psycopg"),
        ("app.web.routes.repairs", "from app.helpers import load_repair"),
        ("app.data.queries", "from app.web import routes"),
        ("app.domains.users", "from app.domains.devices import get_device"),
        ("app.api.routes", "import app"),
        ("app.api.routes", "__import__('app.data')"),
        ("app.api.routes", "importlib.import_module('app.data')"),
        ("app.api.routes", "from importlib import import_module as load"),
        ("app.api.routes", "from builtins import __import__ as load"),
    ],
)
def test_forbidden_dependencies(module, source):
    assert check_source(source, module)


def test_relative_import_from_package_is_checked():
    assert check_source("from .. import repairs", "app.domains.parts", is_package=True)


def test_new_root_helper_requires_explicit_component_assignment():
    assert check_source("from app.data import models", "app.helpers")


def test_technical_modules_cannot_hide_business_dependencies():
    assert check_source("from app.data import models", "app.extensions")
    assert check_source("from app.domains.repairs import get_repair", "app.diagnostics")
    assert check_source("from app.data import models", "app.domains", is_package=True)


@pytest.mark.parametrize("module", ["app.web.errors", "app.api.errors"])
@pytest.mark.parametrize("source", ["from app.data import health", "from app.extensions import db"])
def test_error_renderers_cannot_query_database(module, source):
    assert check_source(source, module)


def test_error_renderers_do_not_import_each_other():
    assert check_source("from app.web.errors import render_error", "app.api.errors")
    assert check_source("from app.api.errors import render_error", "app.web.errors")


@pytest.mark.parametrize("domain", ["users", "devices", "repairs", "parts", "costs"])
@pytest.mark.parametrize(
    "source",
    [
        "from flask import current_app",
        "from werkzeug.security import generate_password_hash",
        "from sqlalchemy import select",
        "from app.data.queries import own_part",
        "from app.extensions import db",
        "from app.bootstrap import create_app",
        "from flask_login import current_user",
        "import itsdangerous",
    ],
)
def test_domains_cannot_import_concrete_infrastructure(domain, source):
    assert check_source(source, f"app.domains.{domain}.service")


@pytest.mark.parametrize(
    "source",
    [
        "from app.domains.parts import PartService",
        "from app.domains.parts.service import PartService",
        "from app.domains.costs import calculate",
    ],
)
def test_data_adapters_depend_only_on_domain_contracts(source):
    assert check_source(source, "app.data.repositories.parts")


def test_domain_packages_import_with_only_standard_library():
    import subprocess
    import sys

    # -S entfernt site-packages: Flask/SQLAlchemy sind gar nicht verfügbar.
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import app.domains.users; import app.domains.devices; "
            "import app.domains.repairs; import app.domains.parts; "
            "import app.domains.costs",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "module, source",
    [
        ("app.domains.repairs.create_repair.handler", "from .ports import RepairRepository"),
        ("app.domains.repairs.create_repair.handler", "from ..model import RepairStatus"),
        ("app.domains.repairs.create_repair.handler", "from .dto import CreateRepair"),
        (
            "app.data.repairs.create_repair",
            "from app.domains.repairs.create_repair.ports import RepairRepository",
        ),
        ("app.domains.parts.add_part.handler", "from app.domains.costs import calculate"),
    ],
)
def test_vertical_slice_allowed_dependencies(module, source):
    assert check_source(source, module) == []


@pytest.mark.parametrize(
    "module, source",
    [
        ("app.domains.repairs.create_repair.handler", "from ..close_repair.handler import execute"),
        ("app.domains.repairs.create_repair.handler", "from ..close_repair.dto import Result"),
        ("app.domains.repairs.model", "from .create_repair.handler import execute"),
        (
            "app.data.repairs.create_repair",
            "from app.domains.repairs.create_repair.handler import execute",
        ),
        ("app.domains.repairs.create_repair.handler", "from app.web.routes import repairs"),
        ("app.domains.repairs.create_repair.handler", "from app.services.repairs import execute"),
    ],
)
def test_vertical_slice_forbidden_dependencies(module, source):
    assert check_source(source, module)


@pytest.mark.parametrize(
    "source",
    [
        "from app.data.users.model import User",
        "from app.domains.users.register_user.handler import execute",
        "from app.web import blueprint",
    ],
)
def test_identity_adapter_cannot_bypass_ports(source):
    assert check_source(source, "app.adapters.users.identity")


def test_identity_adapter_may_use_domain_contract():
    assert (
        check_source(
            "from app.domains.users.dto import UserIdentity", "app.adapters.users.identity"
        )
        == []
    )


@pytest.mark.parametrize("module", ["app.web.routes.users", "app.adapters.users.registration"])
def test_library_http_views_cannot_bypass_user_use_cases(module):
    assert check_source("from flask_security.views import register", module)


@pytest.mark.parametrize("domain", ["devices", "repairs"])
def test_image_slices_keep_storage_and_decoder_outside_domain(domain):
    module = f"app.domains.{domain}.upload_image.handler"
    assert check_source("import boto3", module)
    assert check_source("from PIL import Image", module)
    assert check_source("from app.data.files.storage import ObjectStorage", module)
    assert check_source(f"from app.domains.{domain}.list_images.handler import ListImages", module)
    assert not check_source("from .ports import Storage", module)
