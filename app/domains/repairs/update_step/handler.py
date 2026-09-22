from app.domains.repairs.errors import RepairNotFound
from app.domains.repairs.model import (
    completed,
    description,
    require_id,
    require_owner,
)

from .dto import Command
from .ports import Repository


class UpdateStep:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        require_id(command.repair_id)
        require_id(command.step_id)
        if not self.repository.owns_step(command.owner_id, command.repair_id, command.step_id):
            raise RepairNotFound()
        result = self.repository.update(
            command.owner_id,
            command.repair_id,
            command.step_id,
            description(command.description, maximum=2000),
            completed(command.completed),
        )
        if result is None:
            raise RepairNotFound()
        return result
