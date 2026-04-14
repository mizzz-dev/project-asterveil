from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from game.battle.domain.entities import ActiveEffectState, CombatantState, StatusEffectDefinition
from game.battle.domain.services import BattleState


@dataclass(frozen=True)
class BossPhaseCondition:
    condition_type: str
    value: float


@dataclass(frozen=True)
class BossPhaseEvent:
    event_type: str
    message: str | None = None
    effect_id: str | None = None
    flag_id: str | None = None


@dataclass(frozen=True)
class BossPhaseDefinition:
    phase_id: str
    display_name: str
    ai_profile_id: str | None
    enter_condition: BossPhaseCondition | None
    on_enter_events: tuple[BossPhaseEvent, ...] = tuple()


@dataclass(frozen=True)
class BossEncounterDefinition:
    encounter_id: str
    boss_enemy_id: str
    phases: tuple[BossPhaseDefinition, ...]


@dataclass
class BossPhaseState:
    current_phase_id: str
    transitioned_phase_ids: set[str]


@dataclass(frozen=True)
class BossPhaseTransitionResult:
    active_phase: BossPhaseDefinition
    logs: tuple[str, ...] = tuple()


class BossPhaseService:
    def resolve_phase(
        self,
        state: BattleState,
        actor: CombatantState,
        definition: BossEncounterDefinition,
        runtime_state: BossPhaseState,
        effect_definitions: dict[str, StatusEffectDefinition],
    ) -> BossPhaseTransitionResult:
        phases_by_id = {phase.phase_id: phase for phase in definition.phases}
        current = phases_by_id.get(runtime_state.current_phase_id)
        if current is None:
            current = definition.phases[0]
            runtime_state.current_phase_id = current.phase_id

        logs: list[str] = []
        ordered = list(definition.phases)
        current_index = next((index for index, phase in enumerate(ordered) if phase.phase_id == current.phase_id), 0)
        for phase in ordered[current_index + 1 :]:
            condition = phase.enter_condition
            if condition is None or phase.phase_id in runtime_state.transitioned_phase_ids:
                continue
            if not self._condition_met(actor, condition):
                continue
            runtime_state.current_phase_id = phase.phase_id
            runtime_state.transitioned_phase_ids.add(phase.phase_id)
            logs.append(f"boss_phase_transition:{actor.unit_id}:{current.phase_id}->{phase.phase_id}")
            logs.extend(self._run_on_enter_events(state, actor, phase, effect_definitions))
            current = phase
            break

        logs.append(f"boss_phase_active:{actor.unit_id}:{runtime_state.current_phase_id}")
        return BossPhaseTransitionResult(active_phase=current, logs=tuple(logs))

    def initial_state(self, definition: BossEncounterDefinition) -> BossPhaseState:
        first_phase = definition.phases[0]
        return BossPhaseState(current_phase_id=first_phase.phase_id, transitioned_phase_ids={first_phase.phase_id})

    def _condition_met(self, actor: CombatantState, condition: BossPhaseCondition) -> bool:
        if condition.condition_type == "hp_ratio_below":
            return actor.hp / max(1, actor.max_hp) <= condition.value
        return False

    def _run_on_enter_events(
        self,
        state: BattleState,
        actor: CombatantState,
        phase: BossPhaseDefinition,
        effect_definitions: dict[str, StatusEffectDefinition],
    ) -> list[str]:
        logs: list[str] = []
        for event in phase.on_enter_events:
            if event.event_type == "show_message" and event.message:
                logs.append(f"boss_phase_message:{actor.unit_id}:{event.message}")
                continue
            if event.event_type == "apply_effect_to_self" and event.effect_id:
                definition = effect_definitions.get(event.effect_id)
                if definition is None:
                    logs.append(f"boss_phase_event_skipped:undefined_effect:{event.effect_id}")
                    continue
                existing = next((effect for effect in actor.active_effects if effect.effect_id == event.effect_id), None)
                if existing is None:
                    actor.active_effects.append(
                        ActiveEffectState(effect_id=event.effect_id, remaining_turns=definition.duration_turns)
                    )
                    logs.append(
                        f"boss_phase_effect_applied:{actor.unit_id}:{event.effect_id}:turns={definition.duration_turns}"
                    )
                else:
                    existing.remaining_turns = definition.duration_turns
                    logs.append(
                        f"boss_phase_effect_refreshed:{actor.unit_id}:{event.effect_id}:turns={definition.duration_turns}"
                    )
                continue
            if event.event_type == "set_flag" and event.flag_id:
                logs.append(f"boss_phase_flag_set:{event.flag_id}")
                continue
            logs.append(f"boss_phase_event_skipped:unsupported:{event.event_type}")
        return logs


def parse_boss_phase_condition(raw: dict[str, Any] | None) -> BossPhaseCondition | None:
    if raw is None:
        return None
    condition_type = str(raw.get("type", "")).strip()
    if not condition_type:
        return None
    return BossPhaseCondition(condition_type=condition_type, value=float(raw.get("value", 0)))
