from dataclasses import replace
from decimal import Decimal

from app.domains.costs.model import calculate
from app.domains.repairs.dto import SystemReadAccess
from app.domains.repairs.errors import RepairNotFound
from app.domains.repairs.model import (
    offset,
    require_id,
    require_owner,
)

from .dto import Command
from .ports import Repository


class GetRepair:
    def __init__(self, repository: Repository):
        self.repository = repository

    def execute(self, command: Command):
        if command.owner_id is not SystemReadAccess.ALL_REPAIRS:
            require_owner(command.owner_id)
        require_id(command.repair_id)
        # Der API-Einzelfall enthält alle Schritte und Teile. Nur die Browseransicht
        # nutzt Teilfenster; die Berechtigungs- und Kostenregeln bleiben dieselben.
        part_offset = 0 if command.complete else offset(command.part_offset)
        step_offset = 0 if command.complete else offset(command.offset)
        result = self.repository.get(
            command.owner_id, command.repair_id, step_offset, None if command.complete else 20
        )
        if result is None:
            raise RepairNotFound()
        # Alle Positionen zählen für die Kosten, auch wenn die Oberfläche nur eine
        # Seite zeigt. Die gemeinsame Kostenfunktion bleibt die einzige Formel.
        basis = tuple((part.unit_price, part.quantity) for part in result.parts)
        parts = tuple(
            replace(
                part, total=calculate(Decimal(0), Decimal(0), [(part.unit_price, part.quantity)])
            )
            for part in result.parts[part_offset : None if command.complete else part_offset + 20]
        )
        return replace(
            result,
            parts=parts,
            part_total=len(result.parts),
            part_offset=part_offset,
            labor_cost=calculate(result.hours, result.hourly_rate, ()),
            parts_cost=calculate(Decimal(0), Decimal(0), basis),
            total_cost=calculate(result.hours, result.hourly_rate, basis),
        )
