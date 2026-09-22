"""Stabile Fehlercodes werden erst in der Präsentation übersetzt."""


class InvalidDevice(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("invalid_device")


class DeviceNotFound(LookupError):
    pass


class AuthenticationRequired(PermissionError):
    pass


class ImageNotFound(LookupError):
    """Unbekannte und fremde Bilder haben denselben Fehler."""


class InvalidImage(ValueError):
    pass


class ImageUnavailable(RuntimeError):
    pass
