from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SalvageReturnItem:
    item_id: str
    quantity: int


@dataclass(frozen=True)
class EquipmentSalvageDefinition:
    equipment_id: str
    salvage_enabled: bool
    required_workshop_level: int
    base_returns: tuple[SalvageReturnItem, ...]
    upgrade_bonus_returns: tuple[SalvageReturnItem, ...] = tuple()
    salvage_tags: tuple[str, ...] = tuple()
    description: str = ""


@dataclass(frozen=True)
class EquipmentSalvageEvaluation:
    equipment_id: str
    can_salvage: bool
    code: str
    message: str
    required_workshop_level: int
    returns: tuple[SalvageReturnItem, ...] = tuple()


@dataclass(frozen=True)
class EquipmentSalvageResult:
    success: bool
    code: str
    message: str
    returns: tuple[SalvageReturnItem, ...] = tuple()


class EquipmentSalvageService:
    def __init__(self, definitions: dict[str, EquipmentSalvageDefinition]) -> None:
        self._definitions = definitions

    def definitions(self) -> dict[str, EquipmentSalvageDefinition]:
        return self._definitions

    def resolve_returns(self, equipment_id: str, *, upgrade_level: int) -> tuple[SalvageReturnItem, ...]:
        definition = self._definitions.get(equipment_id)
        if definition is None or not definition.salvage_enabled:
            return tuple()

        resolved: dict[str, int] = {}
        for item in definition.base_returns:
            resolved[item.item_id] = resolved.get(item.item_id, 0) + item.quantity

        if upgrade_level > 0:
            for item in definition.upgrade_bonus_returns:
                resolved[item.item_id] = resolved.get(item.item_id, 0) + (item.quantity * upgrade_level)

        return tuple(
            SalvageReturnItem(item_id=item_id, quantity=quantity)
            for item_id, quantity in sorted(resolved.items())
            if quantity > 0
        )

    def evaluate_salvage(
        self,
        *,
        equipment_id: str,
        inventory_items: dict[str, int],
        workshop_level: int,
        equipped_items: tuple[str, ...],
        upgrade_level: int,
    ) -> EquipmentSalvageEvaluation:
        definition = self._definitions.get(equipment_id)
        if definition is None:
            return EquipmentSalvageEvaluation(
                equipment_id=equipment_id,
                can_salvage=False,
                code="unknown_equipment",
                message=f"equipment_salvage_failed:unknown_equipment:{equipment_id}",
                required_workshop_level=0,
            )
        if not definition.salvage_enabled:
            return EquipmentSalvageEvaluation(
                equipment_id=equipment_id,
                can_salvage=False,
                code="salvage_disabled",
                message=f"equipment_salvage_failed:salvage_disabled:{equipment_id}",
                required_workshop_level=definition.required_workshop_level,
            )

        owned = int(inventory_items.get(equipment_id, 0))
        if owned <= 0:
            return EquipmentSalvageEvaluation(
                equipment_id=equipment_id,
                can_salvage=False,
                code="not_owned",
                message=f"equipment_salvage_failed:not_owned:{equipment_id}",
                required_workshop_level=definition.required_workshop_level,
            )

        equipped_count = sum(1 for eq in equipped_items if eq == equipment_id)
        if owned - equipped_count <= 0:
            return EquipmentSalvageEvaluation(
                equipment_id=equipment_id,
                can_salvage=False,
                code="equipped",
                message=f"equipment_salvage_failed:equipped:{equipment_id}",
                required_workshop_level=definition.required_workshop_level,
            )

        if workshop_level < definition.required_workshop_level:
            return EquipmentSalvageEvaluation(
                equipment_id=equipment_id,
                can_salvage=False,
                code="insufficient_workshop_level",
                message="equipment_salvage_failed:insufficient_workshop_level",
                required_workshop_level=definition.required_workshop_level,
            )

        returns = self.resolve_returns(equipment_id, upgrade_level=upgrade_level)
        return EquipmentSalvageEvaluation(
            equipment_id=equipment_id,
            can_salvage=True,
            code="salvageable",
            message=f"equipment_salvage_ready:{equipment_id}",
            required_workshop_level=definition.required_workshop_level,
            returns=returns,
        )

    def apply_salvage(
        self,
        *,
        equipment_id: str,
        inventory_state: dict,
        workshop_level: int,
        equipped_items: tuple[str, ...],
        upgrade_level: int,
    ) -> EquipmentSalvageResult:
        items = inventory_state.setdefault("items", {})
        evaluation = self.evaluate_salvage(
            equipment_id=equipment_id,
            inventory_items=items,
            workshop_level=workshop_level,
            equipped_items=equipped_items,
            upgrade_level=upgrade_level,
        )
        if not evaluation.can_salvage:
            return EquipmentSalvageResult(False, evaluation.code, evaluation.message)

        items[equipment_id] = int(items.get(equipment_id, 0)) - 1
        if items[equipment_id] <= 0:
            items.pop(equipment_id, None)

        for reward in evaluation.returns:
            items[reward.item_id] = int(items.get(reward.item_id, 0)) + reward.quantity

        return EquipmentSalvageResult(
            success=True,
            code="salvaged",
            message=f"equipment_salvage_success:{equipment_id}",
            returns=evaluation.returns,
        )
