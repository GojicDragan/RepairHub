from dataclasses import replace
from decimal import Decimal

from app.domains.costs.model import calculate
from app.domains.parts.errors import PartNotFound
from app.domains.parts.model import require_id, require_owner, values

from .dto import Command
from .ports import Repository


class AddPart:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        require_owner(command.owner_id)
        require_id(command.repair_id)
        if not self.repository.owns_repair(command.owner_id, command.repair_id):
            raise PartNotFound()
        name, price, count = values(command.name, command.unit_price, command.quantity)
        result = self.repository.add(command.owner_id, command.repair_id, name, price, count)
        if result is None:
            raise PartNotFound()
        return replace(result, total=calculate(Decimal(0), Decimal(0), [(price, count)]))
