"""Gemeinsame Fachregeln; keine Abhängigkeiten zwischen Reparatur-Slices."""

from .errors import AuthenticationRequired, InvalidRepair, RepairNotFound

STATUSES = ("open", "in_progress", "completed")


def require_owner(owner_id):
    if type(owner_id) is not int or owner_id <= 0:
        raise AuthenticationRequired()


def require_id(value):
    # bool ist in Python eine int-Unterklasse, aber keine gültige Objekt-ID.
    # Die Obergrenze entspricht dem Wertebereich der persistenten BIGINT-IDs.
    if type(value) is not int or not 1 <= value <= 9223372036854775807:
        raise RepairNotFound()


def description(value, *, maximum=10000):
    if not isinstance(value, str) or not value.strip():
        raise InvalidRepair("description", "required")
    if len(value.strip()) > maximum:
        raise InvalidRepair("description", "too_long")
    # Mehrzeilige Fehlerbilder erlauben; unsichtbare Steuerzeichen bleiben ungültig.
    if any((ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127 for char in value):
        raise InvalidRepair("description", "control_character")
    return value.strip()


def status(value):
    if value not in STATUSES:
        raise InvalidRepair("status", "invalid_status")
    # Alle drei Zustände bleiben jederzeit erreichbar, auch nach Abschluss.
    return value


def completed(value):
    if type(value) is not bool:
        raise InvalidRepair("completed", "invalid_completed")
    return value


def offset(value):
    if type(value) is not int or not 0 <= value <= 9223372036854775807:
        raise ValueError("invalid_offset")
    return value
