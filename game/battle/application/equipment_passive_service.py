from __future__ import annotations

from dataclasses import dataclass

from game.battle.domain.entities import ActiveEffectState, CombatantState, StatusEffectDefinition


SUPPORTED_PASSIVE_TYPES = {
    "status_resistance",
    "heal_bonus",
    "sp_cost_modifier",
    "battle_start_effect",
    "stat_bonus",
}


@dataclass(frozen=True)
class PassiveEffect:
    passive_id: str
    passive_type: str
    target: str
    parameters: dict[str, object]
    description: str = ""


@dataclass(frozen=True)
class UnitPassiveContext:
    resisted_effects: dict[str, str]
    heal_bonus_rate: float
    sp_cost_rate: float
    battle_start_effects: tuple[tuple[str, str], ...]


class EquipmentPassiveService:
    def __init__(self, passives_by_equipment_id: dict[str, tuple[PassiveEffect, ...]]) -> None:
        self._passives_by_equipment_id = passives_by_equipment_id

    def resolve_equipped_passives(self, equipped: dict[str, str]) -> tuple[PassiveEffect, ...]:
        resolved: list[PassiveEffect] = []
        for equipment_id in equipped.values():
            resolved.extend(self._passives_by_equipment_id.get(equipment_id, tuple()))
        return tuple(resolved)

    def resolve_context(self, equipped: dict[str, str]) -> UnitPassiveContext:
        resisted_effects: dict[str, str] = {}
        heal_bonus_rate = 0.0
        sp_cost_rate = 1.0
        battle_start_effects: list[tuple[str, str]] = []

        for passive in self.resolve_equipped_passives(equipped):
            if passive.passive_type not in SUPPORTED_PASSIVE_TYPES:
                raise ValueError(f"unsupported passive_type: {passive.passive_type} ({passive.passive_id})")
            if passive.target != "self":
                raise ValueError(f"unsupported passive target: {passive.target} ({passive.passive_id})")

            if passive.passive_type == "status_resistance":
                effect_id = str(passive.parameters.get("effect_id") or "")
                if not effect_id:
                    raise ValueError(f"status_resistance requires parameters.effect_id ({passive.passive_id})")
                resisted_effects.setdefault(effect_id, passive.passive_id)
            elif passive.passive_type == "heal_bonus":
                rate = float(passive.parameters.get("rate", 0.0))
                heal_bonus_rate += rate
            elif passive.passive_type == "sp_cost_modifier":
                sp_cost_rate *= max(0.0, float(passive.parameters.get("rate", 1.0)))
            elif passive.passive_type == "battle_start_effect":
                effect_id = str(passive.parameters.get("effect_id") or "")
                if not effect_id:
                    raise ValueError(f"battle_start_effect requires parameters.effect_id ({passive.passive_id})")
                battle_start_effects.append((effect_id, passive.passive_id))

        return UnitPassiveContext(
            resisted_effects=resisted_effects,
            heal_bonus_rate=heal_bonus_rate,
            sp_cost_rate=sp_cost_rate,
            battle_start_effects=tuple(battle_start_effects),
        )

    def apply_battle_start_effects(
        self,
        actor: CombatantState,
        context: UnitPassiveContext,
        effect_definitions: dict[str, StatusEffectDefinition],
    ) -> list[str]:
        logs: list[str] = []
        for effect_id, passive_id in context.battle_start_effects:
            definition = effect_definitions.get(effect_id)
            if definition is None:
                logs.append(f"passive_skipped:undefined_effect:{passive_id}:{effect_id}")
                continue
            existing = next((active for active in actor.active_effects if active.effect_id == effect_id), None)
            if existing is None:
                actor.active_effects.append(
                    ActiveEffectState(effect_id=effect_id, remaining_turns=definition.duration_turns)
                )
                logs.append(
                    f"passive_triggered:battle_start_effect:{actor.unit_id}:{passive_id}:{effect_id}:turns={definition.duration_turns}"
                )
                continue
            existing.remaining_turns = definition.duration_turns
            logs.append(
                f"passive_triggered:battle_start_effect_refresh:{actor.unit_id}:{passive_id}:{effect_id}:turns={definition.duration_turns}"
            )
        return logs

    def apply_heal_bonus(self, base_amount: int, context: UnitPassiveContext | None) -> tuple[int, str | None]:
        if context is None or context.heal_bonus_rate <= 0:
            return base_amount, None
        modified = max(1, int(base_amount * (1.0 + context.heal_bonus_rate)))
        return modified, f"passive_triggered:heal_bonus:rate={context.heal_bonus_rate:.2f}:base={base_amount}:final={modified}"

    def resolve_sp_cost(self, base_cost: int, context: UnitPassiveContext | None) -> tuple[int, str | None]:
        if context is None:
            return base_cost, None
        modified = max(0, int(base_cost * context.sp_cost_rate))
        if modified == base_cost:
            return modified, None
        return modified, f"passive_triggered:sp_cost_modifier:rate={context.sp_cost_rate:.2f}:base={base_cost}:final={modified}"
