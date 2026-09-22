from app.domains.repairs.errors import RepairNotFound
from app.domains.repairs.model import (
    offset,
    require_id,
    require_owner,
)

from .dto import Command
from .ports import Repository


class GetRepair:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        require_id(command.repair_id)
        result = self.repository.get(
            command.owner_id, command.repair_id, offset(command.offset), 20
        )
        if result is None:
            raise RepairNotFound()
        return result
