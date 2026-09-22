from app.domains.devices.model import require_owner

from .dto import Command
from .ports import Repository


class ListDevices:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        # Das 60er-Limit schützt auch direkte AJAX-Aufrufe vor unbegrenzten Listen.
        # Die BIGINT-Grenzen verhindern Überläufe im nachgelagerten Datenadapter.
        if (
            type(command.offset) is not int
            or not 0 <= command.offset <= 9223372036854775807
            or type(command.limit) is not int
            or not 1 <= command.limit <= 60
            or (
                command.snapshot is not None
                and (
                    type(command.snapshot) is not int
                    or not 0 <= command.snapshot <= 9223372036854775807
                )
            )
        ):
            raise ValueError("invalid_window")
        return self.repository.list(
            command.owner_id, command.offset, command.limit, command.snapshot
        )
