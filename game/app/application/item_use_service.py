from __future__ import annotations

from dataclasses import dataclass

from game.save.domain.entities import PartyMemberState


@dataclass(frozen=True)
class ItemUseResult:
    success: bool
    code: str
    message: str


class ItemUseService:
    def use_item(
        self,
        *,
        item_id: str,
        target_character_id: str,
        item_definitions: dict[str, dict],
        party_members: list[PartyMemberState],
        inventory_state: dict,
    ) -> ItemUseResult:
        items = inventory_state.setdefault("items", {})
        owned = int(items.get(item_id, 0))
        if owned <= 0:
            return ItemUseResult(False, "no_stock", f"item_use_failed:no_stock:{item_id}")

        definition = item_definitions.get(item_id)
        if definition is None:
            return ItemUseResult(False, "item_not_defined", f"item_use_failed:item_not_defined:{item_id}")

        target = next((member for member in party_members if member.character_id == target_character_id), None)
        if target is None:
            return ItemUseResult(False, "invalid_target", f"item_use_failed:invalid_target:{target_character_id}")

        if definition.get("target_scope") not in {"single_ally", "self"}:
            return ItemUseResult(False, "invalid_target_scope", f"item_use_failed:unsupported_target_scope:{item_id}")

        effect_type = definition.get("effect_type")
        effect_value = int(definition.get("effect_value", 0))
        if effect_value <= 0:
            return ItemUseResult(False, "invalid_effect", f"item_use_failed:invalid_effect_value:{item_id}")

        applied = False
        if effect_type == "recover_hp":
            before = target.current_hp
            target.current_hp = min(target.max_hp, target.current_hp + effect_value)
            applied = target.current_hp > before
        elif effect_type == "recover_sp":
            before = target.current_sp
            target.current_sp = min(target.max_sp, target.current_sp + effect_value)
            applied = target.current_sp > before
        else:
            return ItemUseResult(False, "unsupported_effect", f"item_use_failed:unsupported_effect:{item_id}")

        if not applied:
            return ItemUseResult(False, "no_effect", f"item_use_failed:no_effect:{item_id}:{target_character_id}")

        items[item_id] = owned - 1
        if items[item_id] <= 0:
            items.pop(item_id)

        return ItemUseResult(True, "used", f"item_used:{item_id}:target={target_character_id}")
