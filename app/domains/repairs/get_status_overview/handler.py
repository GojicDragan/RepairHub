from app.domains.repairs.model import require_owner

from .dto import Command, StatusOverview
from .ports import Repository


class GetStatusOverview:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command) -> StatusOverview:
        require_owner(command.owner_id)
        # Fehlende Gruppen entsprechen null Fällen; der Überblick bleibt ungefiltert.
        counts = self.repository.count_by_status(command.owner_id)
        return StatusOverview(
            counts.get("open", 0), counts.get("in_progress", 0), counts.get("completed", 0)
        )
