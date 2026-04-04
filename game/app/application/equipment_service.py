from __future__ import annotations

from dataclasses import dataclass

from game.save.domain.entities import PartyMemberState


VALID_SLOTS = ("weapon", "armor")
STAT_KEYS = ("hp", "sp", "atk", "defense", "spd")


@dataclass(frozen=True)
class EquipmentDefinition:
    equipment_id: str
    name: str
    slot_type: str
    stat_modifiers: dict[str, int]
    description: str = ""
    price: int = 0
    stackable: bool = False


@dataclass(frozen=True)
class EquipmentResult:
    success: bool
    code: str
    message: str


class EquipmentService:
    def __init__(self, equipment_definitions: dict[str, EquipmentDefinition]) -> None:
        self._equipment_definitions = equipment_definitions

    def compute_bonuses(self, equipped: dict[str, str]) -> dict[str, int]:
        bonus = {key: 0 for key in STAT_KEYS}
        for slot, equipment_id in equipped.items():
            if slot not in VALID_SLOTS:
                continue
            definition = self._equipment_definitions.get(equipment_id)
            if definition is None:
                continue
            for key, value in definition.stat_modifiers.items():
                normalized = "defense" if key == "def" else key
                if normalized in bonus:
                    bonus[normalized] += int(value)
        return bonus

    def resolve_final_stats(self, member: PartyMemberState) -> dict[str, int]:
        bonus = self.compute_bonuses(member.equipped)
        max_hp = max(1, member.max_hp + bonus["hp"])
        max_sp = max(0, member.max_sp + bonus["sp"])
        return {
            "max_hp": max_hp,
            "current_hp": min(max_hp, member.current_hp),
            "max_sp": max_sp,
            "current_sp": min(max_sp, member.current_sp),
            "atk": max(1, member.atk + bonus["atk"]),
            "defense": max(0, member.defense + bonus["defense"]),
            "spd": max(1, member.spd + bonus["spd"]),
        }

    def equip_item(
        self,
        *,
        party_members: list[PartyMemberState],
        inventory_state: dict,
        character_id: str,
        slot_type: str,
        equipment_id: str,
    ) -> EquipmentResult:
        if slot_type not in VALID_SLOTS:
            return EquipmentResult(False, "invalid_slot", f"equip_failed:invalid_slot:{slot_type}")

        member = next((m for m in party_members if m.character_id == character_id), None)
        if member is None:
            return EquipmentResult(False, "invalid_member", f"equip_failed:invalid_member:{character_id}")

        definition = self._equipment_definitions.get(equipment_id)
        if definition is None:
            return EquipmentResult(False, "unknown_equipment", f"equip_failed:unknown_equipment:{equipment_id}")
        if definition.slot_type != slot_type:
            return EquipmentResult(False, "slot_mismatch", f"equip_failed:slot_mismatch:{slot_type}:{equipment_id}")

        currently_equipped = member.equipped.get(slot_type)
        if currently_equipped == equipment_id:
            return EquipmentResult(True, "no_change", f"equip_succeeded:no_change:{character_id}:{slot_type}:{equipment_id}")

        owned = int(inventory_state.get("items", {}).get(equipment_id, 0))
        equipped_count = sum(1 for unit in party_members for eq in unit.equipped.values() if eq == equipment_id)
        available = owned - equipped_count
        if available <= 0:
            return EquipmentResult(False, "insufficient_stock", f"equip_failed:insufficient_stock:{equipment_id}")

        member.equipped[slot_type] = equipment_id
        return EquipmentResult(True, "equipped", f"equip_succeeded:{character_id}:{slot_type}:{equipment_id}")
