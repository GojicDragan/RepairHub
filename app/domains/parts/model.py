from app.domains.costs.model import decimal_value, quantity

from .errors import AuthenticationRequired, InvalidPart, PartNotFound


def require_owner(value):
    if type(value) is not int or value <= 0:
        raise AuthenticationRequired()


def require_id(value):
    if type(value) is not int or not 1 <= value <= 9223372036854775807:
        raise PartNotFound()


def values(name, price, count):
    if not isinstance(name, str) or not name.strip():
        raise InvalidPart("name", "required")
    name = name.strip()
    if len(name) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise InvalidPart("name", "invalid_name")
    try:
        price = decimal_value(price)
    except ValueError:
        raise InvalidPart("unit_price", "invalid_decimal") from None
    try:
        count = quantity(count)
    except ValueError:
        raise InvalidPart("quantity", "invalid_quantity") from None
    return name, price, count
