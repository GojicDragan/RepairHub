from app.domains.devices.errors import DeviceNotFound
from app.domains.devices.model import require_owner, validate

from .dto import Command
from .ports import Repository


class UpdateDevice:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        if type(command.device_id) is not int or not 1 <= command.device_id <= 9223372036854775807:
            raise DeviceNotFound()
        # Eigentümerschaft vor Validierung prüfen: Fremde und unbekannte IDs sind gleich.
        if self.repository.get(command.owner_id, command.device_id) is None:
            raise DeviceNotFound()
        # Die Schreiboperation muss die Eigentumsbedingung erneut atomar anwenden;
        # das vorgängige Lesen ersetzt diese Absicherung nicht.
        device = self.repository.update(
            command.owner_id, command.device_id, validate(command.values)
        )
        if device is None:
            raise DeviceNotFound()
        return device
