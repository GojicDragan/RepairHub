from app.domains.devices.model import require_owner, validate

from .dto import Command
from .ports import Repository


class RegisterDevice:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        return self.repository.create(command.owner_id, validate(command.values))
