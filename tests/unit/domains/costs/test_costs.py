"""Verbindliche Kostenbeispiele und numerische Grenzen ohne Framework."""

from decimal import Decimal

import pytest

from app.domains.costs.model import calculate, decimal_value, quantity


@pytest.mark.parametrize(
    "hours,rate,parts,total",
    [
        ("2", "80", [("15", 3)], "205.00"),
        ("2", "80", [], "160.00"),
        ("0", "0", [("0.10", 3)], "0.30"),
        ("0.01", "0.50", [], "0.01"),
        ("0", "0", [], "0.00"),
    ],
)
def test_cost_examples(hours, rate, parts, total):
    assert calculate(Decimal(hours), Decimal(rate), [(Decimal(p), q) for p, q in parts]) == Decimal(
        total
    )


@pytest.mark.parametrize(
    "value", ["NaN", "Infinity", "-1", "0.001", "1000000000", "", None, True, 0.1, [], "1e99"]
)
def test_invalid_money(value):
    with pytest.raises(ValueError):
        decimal_value(value)


@pytest.mark.parametrize("value", [0, -1, "1.5", 1.5, True, None, "2147483648"])
def test_invalid_quantity(value):
    with pytest.raises(ValueError):
        quantity(value)


def test_large_values_remain_exact():
    assert calculate(
        Decimal("999999.99"), Decimal("999999999.99"), [(Decimal("999999999.99"), 2147483647)]
    ) == Decimal("2148483646968515163.53")


def test_calculation_is_independent_of_global_decimal_precision():
    from decimal import localcontext

    with localcontext() as context:
        context.prec = 3
        assert calculate(Decimal("2"), Decimal("80"), [(Decimal("15"), 3)]) == Decimal("205.00")


def test_numeric_boundaries_are_accepted():
    from app.domains.costs.model import HOURS_MAX

    assert decimal_value("999999.99", HOURS_MAX) == HOURS_MAX
    assert decimal_value("999999999.99") == Decimal("999999999.99")
    assert decimal_value("0") == 0
    assert quantity("2147483647") == 2147483647
