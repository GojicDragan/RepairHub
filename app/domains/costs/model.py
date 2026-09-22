"""Reine Dezimalregeln und Kostenformel, ohne Datenzugriff oder Framework."""

import re
from decimal import ROUND_HALF_UP, Decimal, localcontext

MONEY_MAX = Decimal("999999999.99")
HOURS_MAX = Decimal("999999.99")


def decimal_value(value, maximum=MONEY_MAX):
    # Keine binären Floats oder impliziten bool-Werte in Geldbeträge umwandeln.
    if type(value) not in (str, int, Decimal):
        raise ValueError("invalid_decimal")
    text = str(value).strip()
    if len(text) > 32 or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", text):
        raise ValueError("invalid_decimal")
    result = Decimal(text)
    if result > maximum:
        raise ValueError("invalid_decimal")
    return result


def quantity(value):
    if type(value) not in (str, int):
        raise ValueError("invalid_quantity")
    text = str(value).strip()
    if len(text) > 10 or not re.fullmatch(r"[0-9]+", text) or not 1 <= int(text) <= 2147483647:
        raise ValueError("invalid_quantity")
    return int(text)


def calculate(hours, hourly_rate, parts):
    # Erst die Gesamtsumme runden. Ein eigener Kontext hält auch grosse gültige
    # Produkte exakt und unabhängig von fremden Änderungen am Decimal-Kontext.
    with localcontext() as context:
        context.prec = 50
        total = hours * hourly_rate + sum((price * count for price, count in parts), Decimal(0))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
