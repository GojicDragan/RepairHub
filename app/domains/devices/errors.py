"""Stabile Fehlercodes werden erst in der Präsentation übersetzt."""


class InvalidDevice(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("invalid_device")


class DeviceNotFound(LookupError):
    pass


class AuthenticationRequired(PermissionError):
    pass
