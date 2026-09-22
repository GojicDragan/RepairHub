from app.domains.repairs.errors import RepairNotFound
from app.domains.repairs.model import (
    description,
    require_id,
    require_owner,
)

from .dto import Command
from .ports import Repository


class AddStep:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        require_id(command.repair_id)
        if not self.repository.owns_repair(command.owner_id, command.repair_id):
            raise RepairNotFound()
        result = self.repository.add(
            command.owner_id,
            command.repair_id,
            description(command.description, maximum=2000),
            False,
        )
        if result is None:
            raise RepairNotFound()
        return result
