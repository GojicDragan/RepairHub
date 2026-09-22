from app.domains.repairs.dto import Image
from app.domains.repairs.errors import ImageNotFound, ImageUnavailable, InvalidImage
from app.domains.repairs.model import require_owner

from .dto import Command
from .ports import KeyFactory, Processor, Repository, Storage


class UploadImage:
    def __init__(
        self, repository: Repository, processor: Processor, storage: Storage, new_key: KeyFactory
    ):
        self.repository, self.processor, self.storage = repository, processor, storage
        self.new_key = new_key

    def execute(self, command: Command) -> Image:
        require_owner(command.owner_id)
        if (
            type(command.parent_id) is not int
            or command.parent_id <= 0
            or not self.repository.owns(command.owner_id, command.parent_id)
        ):
            raise ImageNotFound()
        name = command.filename
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name) > 200
            or any(ord(c) < 32 or ord(c) == 127 or c in "/\\" for c in name)
            or not isinstance(command.content, bytes)
            or not 0 < len(command.content) <= 10 * 1024 * 1024
        ):
            raise InvalidImage()
        try:
            original, thumbnail, width, height = self.processor.prepare(command.content)
        except ValueError:
            raise InvalidImage() from None
        image = Image(self.new_key(), name.strip(), width, height)
        try:
            self.storage.put(f"images/{image.id}.webp", original, "image/webp")
            self.storage.put(f"images/{image.id}-thumb.webp", thumbnail, "image/webp")
            # Erst vollständige Objekte veröffentlichen. Bei unklarer DB-Commit-Antwort
            # nichts löschen: Ein tatsächlich gespeicherter Verweis muss gültig bleiben.
            self.repository.add(command.owner_id, command.parent_id, image)
        except OSError:
            raise ImageUnavailable() from None
        return image
