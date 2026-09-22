from app.domains.repairs.errors import RepairNotFound
from app.domains.repairs.model import (
    description,
    require_id,
    require_owner,
)

from .dto import Command
from .ports import Repository


class CreateRepair:
    def __init__(self, repository: Repository, clock):
        self.repository = repository
        self.clock = clock

    def execute(self, command: Command):
        require_owner(command.owner_id)
        require_id(command.device_id)
        if not self.repository.owns_device(command.owner_id, command.device_id):
            raise RepairNotFound()
        result = self.repository.create(
            command.owner_id,
            command.device_id,
            description(command.description),
            "open",
            self.clock(),
        )
        # Die Zuordnung kann nach der Vorprüfung verschwunden sein; der Adapter
        # prüft sie deshalb nochmals innerhalb der Schreibtransaktion.
        if result is None:
            raise RepairNotFound()
        return result
