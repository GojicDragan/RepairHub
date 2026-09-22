import re

from app.domains.repairs.errors import ImageNotFound, ImageUnavailable
from app.domains.repairs.model import require_owner

from .dto import Command
from .ports import Repository


class DeleteImage:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command) -> None:
        require_owner(command.owner_id)
        if (
            type(command.parent_id) is not int
            or command.parent_id <= 0
            or not isinstance(command.image_id, str)
            or not re.fullmatch(r"[a-f0-9]{32}", command.image_id)
        ):
            raise ImageNotFound()
        try:
            removed = self.repository.delete(command.owner_id, command.parent_id, command.image_id)
        except OSError:
            raise ImageUnavailable() from None
        if not removed:
            raise ImageNotFound()
