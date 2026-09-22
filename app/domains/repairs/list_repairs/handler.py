from app.domains.repairs.dto import SystemReadAccess
from app.domains.repairs.errors import RepairNotFound
from app.domains.repairs.model import (
    STATUSES,
    offset,
    require_id,
    require_owner,
)

from .dto import Command
from .ports import Repository


class ListRepairs:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        if command.owner_id is not SystemReadAccess.ALL_REPAIRS:
            require_owner(command.owner_id)
        if command.device_id is not None:
            require_id(command.device_id)
            if (
                command.owner_id is not SystemReadAccess.ALL_REPAIRS
                and not self.repository.owns_device(command.owner_id, command.device_id)
            ):
                raise RepairNotFound()
        # Das AJAX-Fenster bleibt begrenzt; die obere ID stabilisiert die Liste bei Neuanlagen.
        if type(command.limit) is not int or not 1 <= command.limit <= 60:
            raise ValueError("invalid_window")
        if command.snapshot is not None:
            offset(command.snapshot)
        if (
            not isinstance(command.search, str)
            or len(command.search) > 200
            or any(ord(char) < 32 or ord(char) == 127 for char in command.search)
        ):
            raise ValueError("invalid_search")
        if command.status_filter not in ("", *STATUSES):
            raise ValueError("invalid_status_filter")
        result = self.repository.list(
            command.owner_id,
            command.device_id,
            offset(command.offset),
            command.limit,
            command.snapshot,
            " ".join(command.search.split()),
            command.status_filter,
        )
        if result is None:
            raise RepairNotFound()
        return result
