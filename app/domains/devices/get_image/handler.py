import re

from app.domains.devices.errors import ImageNotFound, ImageUnavailable
from app.domains.devices.model import require_owner

from .dto import Command
from .ports import Repository, Storage


class GetImage:
    def __init__(self, repository: Repository, storage: Storage):
        self.repository, self.storage = repository, storage

    def execute(self, command: Command) -> bytes:
        require_owner(command.owner_id)
        if (
            type(command.parent_id) is not int
            or command.parent_id <= 0
            or not isinstance(command.image_id, str)
            or not re.fullmatch(r"[a-f0-9]{32}", command.image_id)
        ):
            raise ImageNotFound()
        image = self.repository.get(command.owner_id, command.parent_id, command.image_id)
        if image is None:
            raise ImageNotFound()
        suffix = "-thumb" if command.thumbnail else ""
        try:
            return self.storage.read(f"images/{image.id}{suffix}.webp")
        except OSError:
            raise ImageUnavailable() from None
