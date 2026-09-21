"""Jeder Test gehört anhand seines Verzeichnisses genau einer Teststufe an."""

from pathlib import Path

import pytest

SUITES = {"unit", "integration", "e2e"}


def pytest_collection_modifyitems(items):
    test_root = Path(__file__).parent
    for item in items:
        suite = item.path.relative_to(test_root).parts[0]
        if suite not in SUITES:
            raise pytest.UsageError(f"Test ausserhalb von unit/integration/e2e: {item.nodeid}")
        existing = {marker.name for marker in item.iter_markers()} & SUITES
        if existing - {suite}:
            raise pytest.UsageError(f"Widersprüchliche Teststufe: {item.nodeid}")
        item.add_marker(getattr(pytest.mark, suite))
