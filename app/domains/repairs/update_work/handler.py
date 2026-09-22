from app.domains.costs.model import HOURS_MAX, MONEY_MAX, decimal_value
from app.domains.repairs.errors import InvalidRepair, RepairNotFound
from app.domains.repairs.model import require_id, require_owner

from .dto import Command
from .ports import Repository


class UpdateWork:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        require_id(command.repair_id)
        if not self.repository.owns_repair(command.owner_id, command.repair_id):
            raise RepairNotFound()
        values = []
        for field, maximum in [("hours", HOURS_MAX), ("hourly_rate", MONEY_MAX)]:
            try:
                values.append(decimal_value(getattr(command, field), maximum))
            except ValueError:
                raise InvalidRepair(field, "invalid_decimal") from None
        result = self.repository.update(command.owner_id, command.repair_id, *values)
        if result is None:
            raise RepairNotFound()
        return result
