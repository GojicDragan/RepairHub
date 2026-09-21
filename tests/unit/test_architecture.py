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
        ("app.web.routes.repairs", "from app.services.repairs import get_repair"),
        ("app.api.routes", "from app.services.users import verify_token"),
        ("app.services.repairs", "from app.services.costs import calculate"),
        ("app.services.parts", "from app.data.queries import own_part"),
        ("app.services.costs", "from decimal import Decimal"),
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
        ("app.api.routes", "from app.services.parts import get_part"),
        ("app.api.routes", "import app.services.devices as devices"),
        ("app.services.parts", "from app.services.repairs import get_repair"),
        ("app.services.costs", "from ..data import queries"),
        ("app.services.costs", "from flask import current_app"),
        ("app.services.costs", "import sqlalchemy"),
        ("app.web.routes.repairs", "from app.extensions import db as store"),
        ("app.web.routes.repairs", "import psycopg"),
        ("app.web.routes.repairs", "from app.helpers import load_repair"),
        ("app.data.queries", "from app.web import routes"),
        ("app.services.users", "from app.services.devices import get_device"),
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
    assert check_source("from .. import repairs", "app.services.parts", is_package=True)


def test_new_root_helper_requires_explicit_component_assignment():
    assert check_source("from app.data import models", "app.helpers")


def test_technical_modules_cannot_hide_business_dependencies():
    assert check_source("from app.data import models", "app.extensions")
    assert check_source("from app.services.repairs import get_repair", "app.diagnostics")
    assert check_source("from app.data import models", "app.services", is_package=True)
