from app.domains.devices.errors import ImageNotFound
from app.domains.devices.model import require_owner

from .dto import Command
from .ports import Repository


class ListImages:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        if (
            type(command.parent_id) is not int
            or command.parent_id <= 0
            or not self.repository.owns(command.owner_id, command.parent_id)
        ):
            raise ImageNotFound()
        if type(command.offset) is not int or command.offset < 0:
            raise ValueError("invalid_offset")
        return self.repository.list(command.owner_id, command.parent_id, command.offset, 24)
