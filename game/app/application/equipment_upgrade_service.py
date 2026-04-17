from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpgradeRequiredItem:
    item_id: str
    quantity: int


@dataclass(frozen=True)
class EquipmentUpgradeLevelDefinition:
    upgrade_level: int
    required_workshop_level: int
    required_items: tuple[UpgradeRequiredItem, ...]
    stat_bonus: dict[str, int]
    passive_modifiers: tuple[dict[str, object], ...] = tuple()
    description: str = ""


@dataclass(frozen=True)
class EquipmentUpgradeDefinition:
    equipment_id: str
    upgrade_enabled: bool
    upgrade_levels: tuple[EquipmentUpgradeLevelDefinition, ...]


@dataclass(frozen=True)
class EquipmentUpgradeEvaluation:
    equipment_id: str
    current_level: int
    max_level: int
    can_upgrade: bool
    code: str
    message: str
    next_level: EquipmentUpgradeLevelDefinition | None


@dataclass(frozen=True)
class EquipmentUpgradeResult:
    success: bool
    code: str
    message: str
    applied_level: int | None = None


class EquipmentUpgradeService:
    def __init__(self, definitions: dict[str, EquipmentUpgradeDefinition]) -> None:
        self._definitions = definitions

    def current_level(self, equipment_id: str, equipment_upgrade_levels: dict[str, int]) -> int:
        return max(0, int(equipment_upgrade_levels.get(equipment_id, 0)))

    def evaluate_upgrade(
        self,
        *,
        equipment_id: str,
        equipment_upgrade_levels: dict[str, int],
        inventory_items: dict[str, int],
        workshop_level: int,
    ) -> EquipmentUpgradeEvaluation:
        definition = self._definitions.get(equipment_id)
        if definition is None:
            return EquipmentUpgradeEvaluation(
                equipment_id=equipment_id,
                current_level=0,
                max_level=0,
                can_upgrade=False,
                code="unknown_equipment",
                message=f"equipment_upgrade_failed:unknown_equipment:{equipment_id}",
                next_level=None,
            )
        if not definition.upgrade_enabled:
            return EquipmentUpgradeEvaluation(
                equipment_id=equipment_id,
                current_level=0,
                max_level=0,
                can_upgrade=False,
                code="upgrade_disabled",
                message=f"equipment_upgrade_failed:upgrade_disabled:{equipment_id}",
                next_level=None,
            )

        max_level = max((entry.upgrade_level for entry in definition.upgrade_levels), default=0)
        current_level = self.current_level(equipment_id, equipment_upgrade_levels)
        next_level = next((entry for entry in definition.upgrade_levels if entry.upgrade_level == current_level + 1), None)
        if next_level is None:
            return EquipmentUpgradeEvaluation(
                equipment_id=equipment_id,
                current_level=current_level,
                max_level=max_level,
                can_upgrade=False,
                code="max_level",
                message=f"equipment_upgrade_failed:max_level:{equipment_id}",
                next_level=None,
            )

        if workshop_level < next_level.required_workshop_level:
            return EquipmentUpgradeEvaluation(
                equipment_id=equipment_id,
                current_level=current_level,
                max_level=max_level,
                can_upgrade=False,
                code="insufficient_workshop_level",
                message="equipment_upgrade_failed:insufficient_workshop_level",
                next_level=next_level,
            )

        for req in next_level.required_items:
            owned = int(inventory_items.get(req.item_id, 0))
            if owned < req.quantity:
                return EquipmentUpgradeEvaluation(
                    equipment_id=equipment_id,
                    current_level=current_level,
                    max_level=max_level,
                    can_upgrade=False,
                    code="insufficient_materials",
                    message="equipment_upgrade_failed:insufficient_materials",
                    next_level=next_level,
                )

        return EquipmentUpgradeEvaluation(
            equipment_id=equipment_id,
            current_level=current_level,
            max_level=max_level,
            can_upgrade=True,
            code="upgradable",
            message=f"equipment_upgrade_ready:{equipment_id}:to_level={current_level + 1}",
            next_level=next_level,
        )

    def apply_upgrade(
        self,
        *,
        equipment_id: str,
        equipment_upgrade_levels: dict[str, int],
        inventory_state: dict,
        workshop_level: int,
    ) -> EquipmentUpgradeResult:
        items = inventory_state.setdefault("items", {})
        evaluation = self.evaluate_upgrade(
            equipment_id=equipment_id,
            equipment_upgrade_levels=equipment_upgrade_levels,
            inventory_items=items,
            workshop_level=workshop_level,
        )
        if not evaluation.can_upgrade or evaluation.next_level is None:
            return EquipmentUpgradeResult(False, evaluation.code, evaluation.message)

        for req in evaluation.next_level.required_items:
            items[req.item_id] = int(items.get(req.item_id, 0)) - req.quantity
            if items[req.item_id] <= 0:
                items.pop(req.item_id, None)

        equipment_upgrade_levels[equipment_id] = evaluation.next_level.upgrade_level
        return EquipmentUpgradeResult(
            True,
            "upgraded",
            f"equipment_upgrade_success:{equipment_id}:upgrade_level:+1:current={evaluation.next_level.upgrade_level}",
            applied_level=evaluation.next_level.upgrade_level,
        )

    def stat_bonus_for_equipment(
        self,
        *,
        equipment_id: str,
        equipment_upgrade_levels: dict[str, int],
    ) -> dict[str, int]:
        definition = self._definitions.get(equipment_id)
        if definition is None or not definition.upgrade_enabled:
            return {}
        current_level = self.current_level(equipment_id, equipment_upgrade_levels)
        aggregate: dict[str, int] = {}
        for level in definition.upgrade_levels:
            if level.upgrade_level > current_level:
                continue
            for key, amount in level.stat_bonus.items():
                aggregate[key] = aggregate.get(key, 0) + int(amount)
        return aggregate

    def definitions(self) -> dict[str, EquipmentUpgradeDefinition]:
        return self._definitions
