from __future__ import annotations

from dataclasses import dataclass

from .entities import (
    ActionCommand,
    ActionResult,
    CombatantState,
    SkillDefinition,
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


def calculate_damage(attacker: CombatantState, target: CombatantState, power: float) -> int:
    scaled_attack = int(attacker.atk * power)
    raw = scaled_attack - target.defense
    return max(1, raw)


def apply_action(
    state: BattleState,
    command: ActionCommand,
    skills: dict[str, SkillDefinition],
) -> ActionResult:
    attacker = state.combatants[command.actor_id]
    target = state.combatants[command.target_id]

    if command.action_type == "attack":
        power = BASE_ATTACK_POWER
        skill_id = None
    elif command.action_type == "skill":
        if command.skill_id is None:
            raise ValueError("skill action requires skill_id")
        skill = skills[command.skill_id]
        if attacker.sp < skill.sp_cost:
            raise ValueError(f"SP不足: actor={attacker.unit_id}, skill={skill.id}")
        attacker.sp -= skill.sp_cost
        power = skill.power
        skill_id = skill.id
    else:
        raise ValueError(f"Unsupported action_type: {command.action_type}")

    damage = calculate_damage(attacker, target, power)
    target.apply_damage(damage)
    return ActionResult(
        actor_id=attacker.unit_id,
        target_id=target.unit_id,
        action_type=command.action_type,
        skill_id=skill_id,
        damage=damage,
        target_hp_after=target.hp,
        target_alive=target.alive,
    )


def execute_turn(
    state: BattleState,
    actor_id: str,
    command_factory,
    skills: dict[str, SkillDefinition],
) -> TurnResult:
    if state.is_finished():
        return TurnResult(acted=False, actor_id=None, summary=None, winner=state.winner())

    actor = state.combatants[actor_id]
    if not actor.alive:
        return TurnResult(acted=False, actor_id=actor.unit_id, summary=None, winner=state.winner())

    command = command_factory(state, actor)
    result = apply_action(state, command, skills)
    return TurnResult(acted=True, actor_id=actor.unit_id, summary=result, winner=state.winner())
