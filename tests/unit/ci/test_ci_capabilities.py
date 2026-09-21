"""Future schema/API implementation cannot silently retain disabled deployment checks."""

import importlib.util
from pathlib import Path

import pytest

ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
)
SCRIPT = ROOT / "scripts" / "ci" / "check_capabilities.py"
spec = importlib.util.spec_from_file_location("capability_gate", SCRIPT)
capability_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capability_gate)


def test_minimal_scaffold_has_no_schema_or_api():
    capability_gate.validate({"schema_migrations": False, "authenticated_api": False}, [], set())


@pytest.mark.parametrize(
    ("migrations", "routes"),
    [([Path("initial.py")], set()), ([], {"/api/auth/token"})],
)
def test_new_capability_requires_deployment_gate(migrations, routes):
    with pytest.raises(ValueError, match="stimmt nicht"):
        capability_gate.validate(
            {"schema_migrations": False, "authenticated_api": False}, migrations, routes
        )
