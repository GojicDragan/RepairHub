from app.domains.devices.errors import DeviceNotFound
from app.domains.devices.model import require_owner

from .dto import Command
from .ports import Repository


class GetDevice:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        # bool ist in Python eine int-Unterklasse, aber keine gültige Geräte-ID.
        # Ausserhalb des BIGINT-Bereichs wie ein unbekanntes Gerät behandeln.
        if type(command.device_id) is not int or not 1 <= command.device_id <= 9223372036854775807:
            raise DeviceNotFound()
        device = self.repository.get(command.owner_id, command.device_id)
        if device is None:
            raise DeviceNotFound()
        return device
