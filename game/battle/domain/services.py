from __future__ import annotations

from dataclasses import dataclass

from .entities import (
    ActiveEffectState,
    ActionCommand,
    ActionResult,
    CombatantState,
    SkillDefinition,
    StatusEffectDefinition,
    TargetResult,
    Team,
    TurnResult,
)


BASE_ATTACK_POWER = 1.0


@dataclass
class BattleState:
    combatants: dict[str, CombatantState]

    def is_finished(self) -> bool:
        return self.winner() is not None

    def winner(self) -> Team | None:
        player_alive = any(c.alive for c in self.combatants.values() if c.team == Team.PLAYER)
        enemy_alive = any(c.alive for c in self.combatants.values() if c.team == Team.ENEMY)

        if player_alive and enemy_alive:
            return None
        if player_alive:
            return Team.PLAYER
        if enemy_alive:
            return Team.ENEMY
        return None

    def turn_order(self) -> list[str]:
        living = [c for c in self.combatants.values() if c.alive]
        living.sort(key=lambda c: (-c.spd, c.unit_id))
        return [c.unit_id for c in living]


def _active_effect(
    combatant: CombatantState,
    effect_id: str,
) -> ActiveEffectState | None:
    return next((effect for effect in combatant.active_effects if effect.effect_id == effect_id), None)


def _effective_stat(
    combatant: CombatantState,
    stat_name: str,
    effect_definitions: dict[str, StatusEffectDefinition],
) -> int:
    base = int(getattr(combatant, stat_name))
    ratio = 1.0
    for active in combatant.active_effects:
        definition = effect_definitions.get(active.effect_id)
        if definition is None:
            continue
        if definition.application_rule != "while_active":
            continue
        if definition.target_stat != stat_name:
            continue
        ratio += definition.magnitude
    return max(1, int(base * max(0.1, ratio)))


def calculate_damage(
    attacker: CombatantState,
    target: CombatantState,
    power: float,
    effect_definitions: dict[str, StatusEffectDefinition],
) -> int:
    scaled_attack = int(_effective_stat(attacker, "atk", effect_definitions) * power)
    raw = scaled_attack - _effective_stat(target, "defense", effect_definitions)
    return max(1, raw)


def _apply_effect(
    target: CombatantState,
    effect_id: str,
    effect_definitions: dict[str, StatusEffectDefinition],
) -> str:
    definition = effect_definitions.get(effect_id)
    if definition is None:
        return f"effect_skipped:undefined:{effect_id}"
    existing = _active_effect(target, effect_id)
    if existing is None:
        target.active_effects.append(ActiveEffectState(effect_id=effect_id, remaining_turns=definition.duration_turns))
        return f"effect_applied:{target.unit_id}:{effect_id}:turns={definition.duration_turns}"
    # 最小仕様: 再付与時は残りターンを上書き
    existing.remaining_turns = definition.duration_turns
    return f"effect_refreshed:{target.unit_id}:{effect_id}:turns={definition.duration_turns}"


def _tick_end_of_turn_effects(
    actor: CombatantState,
    effect_definitions: dict[str, StatusEffectDefinition],
) -> list[str]:
    logs: list[str] = []
    retained: list[ActiveEffectState] = []
    for active in actor.active_effects:
        definition = effect_definitions.get(active.effect_id)
        if definition is None:
            continue
        if definition.application_rule == "per_turn" and definition.effect_type == "ailment":
            damage = max(1, int(actor.max_hp * definition.magnitude))
            actor.apply_damage(damage)
            logs.append(f"effect_tick:{actor.unit_id}:{definition.effect_id}:damage={damage}:hp={actor.hp}")

        active.remaining_turns -= 1
        if active.remaining_turns <= 0:
            logs.append(f"effect_expired:{actor.unit_id}:{active.effect_id}")
            continue
        retained.append(active)
    actor.active_effects = retained
    return logs


def apply_action(
    state: BattleState,
    command: ActionCommand,
    skills: dict[str, SkillDefinition],
    effect_definitions: dict[str, StatusEffectDefinition] | None = None,
) -> ActionResult:
    effect_definitions = effect_definitions or {}
    attacker = state.combatants[command.actor_id]
    logs: list[str] = []

    if command.action_type == "attack":
        power = BASE_ATTACK_POWER
        skill_id = None
        target_scope = "single_enemy"
    elif command.action_type == "skill":
        if command.skill_id is None:
            raise ValueError("skill action requires skill_id")
        skill = skills[command.skill_id]
        if attacker.sp < skill.sp_cost:
            raise ValueError(f"SP不足: actor={attacker.unit_id}, skill={skill.id}")
        attacker.sp -= skill.sp_cost
        power = skill.power
        skill_id = skill.id
        target_scope = skill.target_scope
    else:
        raise ValueError(f"Unsupported action_type: {command.action_type}")

    targets = _resolve_targets(state, attacker, target_scope, command.target_id)
    per_target: list[TargetResult] = []
    for target in targets:
        if command.action_type == "skill":
            for effect_id in skill.apply_effect_ids:
                logs.append(_apply_effect(target, effect_id, effect_definitions))
        damage = calculate_damage(attacker, target, power, effect_definitions)
        target.apply_damage(damage)
        per_target.append(
            TargetResult(
                target_id=target.unit_id,
                damage=damage,
                target_hp_after=target.hp,
                target_alive=target.alive,
            )
        )
    head = per_target[0]
    return ActionResult(
        actor_id=attacker.unit_id,
        action_type=command.action_type,
        skill_id=skill_id,
        target_id=head.target_id,
        damage=head.damage,
        target_hp_after=head.target_hp_after,
        target_alive=head.target_alive,
        target_results=tuple(per_target),
        logs=tuple(logs),
    )


def _resolve_targets(
    state: BattleState,
    attacker: CombatantState,
    target_scope: str,
    target_id: str | None,
) -> list[CombatantState]:
    enemy_team = Team.ENEMY if attacker.team == Team.PLAYER else Team.PLAYER
    living = [unit for unit in state.combatants.values() if unit.team == enemy_team and unit.alive]
    living.sort(key=lambda unit: unit.unit_id)
    if not living:
        raise ValueError("対象となる生存ユニットが存在しません")

    if target_scope == "all_enemies":
        return living
    if target_scope != "single_enemy":
        raise ValueError(f"未対応のtarget_scopeです: {target_scope}")
    if target_id is None:
        raise ValueError("single_enemy の行動には target_id が必要です")

    target = state.combatants.get(target_id)
    if target is None:
        raise ValueError(f"target_id が不正です: {target_id}")
    if target.team != enemy_team:
        raise ValueError(f"対象チームが不正です: actor={attacker.team.value}, target={target.team.value}")
    if not target.alive:
        raise ValueError(f"撃破済み対象は選択できません: {target_id}")
    return [target]


def execute_turn(
    state: BattleState,
    actor_id: str,
    command_factory,
    skills: dict[str, SkillDefinition],
    effect_definitions: dict[str, StatusEffectDefinition] | None = None,
) -> TurnResult:
    if state.is_finished():
        return TurnResult(acted=False, actor_id=None, summary=None, winner=state.winner(), logs=tuple())

    actor = state.combatants[actor_id]
    if not actor.alive:
        return TurnResult(acted=False, actor_id=actor.unit_id, summary=None, winner=state.winner(), logs=tuple())

    command = command_factory(state, actor)
    result = apply_action(state, command, skills, effect_definitions)
    logs = list(result.logs)
    logs.extend(_tick_end_of_turn_effects(actor, effect_definitions or {}))
    return TurnResult(acted=True, actor_id=actor.unit_id, summary=result, winner=state.winner(), logs=tuple(logs))
