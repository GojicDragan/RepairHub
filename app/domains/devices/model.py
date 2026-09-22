"""Gemeinsame Regeln für Erfassung und Änderung eines privaten Geräts."""

from .dto import DeviceValues
from .errors import AuthenticationRequired, InvalidDevice

MAX_LENGTH = 120


def require_owner(owner_id):
    # Die Webschicht ermittelt die Identität; anonyme Aufrufe bleiben auch im Kern gesperrt.
    if type(owner_id) is not int or owner_id <= 0:
        raise AuthenticationRequired()


def validate(values: DeviceValues) -> DeviceValues:
    cleaned = {}
    errors = {}
    for name in ("name", "manufacturer", "model"):
        value = getattr(values, name)
        if not isinstance(value, str) or not value.strip():
            errors[name] = "required"
        elif len(value.strip()) > MAX_LENGTH:
            errors[name] = "too_long"
        elif any(ord(character) < 32 or ord(character) == 127 for character in value):
            errors[name] = "control_character"
        else:
            cleaned[name] = value.strip()
    if errors:
        raise InvalidDevice(errors)
    return DeviceValues(**cleaned)
