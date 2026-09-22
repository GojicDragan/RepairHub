class RepairNotFound(Exception):
    """Fremde und unbekannte Geräte, Fälle und Schritte sind nicht unterscheidbar."""


class AuthenticationRequired(Exception):
    pass


class InvalidRepair(ValueError):
    def __init__(self, field, code):
        self.errors = {field: code}
        super().__init__(code)
