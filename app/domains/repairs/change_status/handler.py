from app.domains.repairs.errors import RepairNotFound
from app.domains.repairs.model import (
    require_id,
    require_owner,
    status,
)

from .dto import Command
from .ports import Repository


class ChangeStatus:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        require_id(command.repair_id)
        if not self.repository.owns_repair(command.owner_id, command.repair_id):
            raise RepairNotFound()
        result = self.repository.change(command.owner_id, command.repair_id, status(command.status))
        if result is None:
            raise RepairNotFound()
        return result
