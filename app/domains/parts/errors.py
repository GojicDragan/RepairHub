class PartNotFound(Exception):
    """Unbekannte und fremde Positionen sind nicht unterscheidbar."""


class AuthenticationRequired(Exception):
    pass


class InvalidPart(ValueError):
    def __init__(self, field, code):
        self.errors = {field: code}
        super().__init__(code)
