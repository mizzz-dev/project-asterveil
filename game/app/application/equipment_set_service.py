from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_SET_BONUS_TYPES = {
    "stat_bonus",
    "passive_effect",
    "status_resistance",
    "skill_modifier",
}


@dataclass(frozen=True)
class EquipmentSetBonusDefinition:
    required_piece_count: int
    bonus_type: str
    parameters: dict[str, object]
    bonus_description: str = ""


@dataclass(frozen=True)
class EquipmentSetDefinition:
    set_id: str
    name: str
    description: str
    member_equipment_ids: tuple[str, ...]
    set_bonuses: tuple[EquipmentSetBonusDefinition, ...]


@dataclass(frozen=True)
class ActiveSetBonus:
    set_id: str
    set_name: str
    required_piece_count: int
    equipped_piece_count: int
    bonus_type: str
    parameters: dict[str, object]
    bonus_description: str


class EquipmentSetService:
    def __init__(self, definitions: dict[str, EquipmentSetDefinition]) -> None:
        self._definitions = definitions

    def resolve_active_bonuses(self, equipped: dict[str, str]) -> tuple[ActiveSetBonus, ...]:
        equipped_ids = {equipment_id for equipment_id in equipped.values() if equipment_id}
        active: list[ActiveSetBonus] = []
        for definition in self._definitions.values():
            piece_count = sum(1 for equipment_id in definition.member_equipment_ids if equipment_id in equipped_ids)
            if piece_count <= 0:
                continue
            for bonus in sorted(definition.set_bonuses, key=lambda item: item.required_piece_count):
                if piece_count < bonus.required_piece_count:
                    continue
                active.append(
                    ActiveSetBonus(
                        set_id=definition.set_id,
                        set_name=definition.name,
                        required_piece_count=bonus.required_piece_count,
                        equipped_piece_count=piece_count,
                        bonus_type=bonus.bonus_type,
                        parameters=dict(bonus.parameters),
                        bonus_description=bonus.bonus_description,
                    )
                )
        return tuple(active)

    def compute_stat_bonus(self, equipped: dict[str, str]) -> dict[str, int]:
        bonus = {"hp": 0, "sp": 0, "atk": 0, "defense": 0, "spd": 0}
        for active in self.resolve_active_bonuses(equipped):
            if active.bonus_type != "stat_bonus":
                continue
            for key, value in active.parameters.items():
                normalized = "defense" if key == "def" else str(key)
                if normalized in bonus:
                    bonus[normalized] += int(value)
        return bonus
