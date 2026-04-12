from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from game.battle.domain.entities import ActionCommand, CombatantState, SkillDefinition, Team
from game.battle.domain.services import BattleState


InputReader = Callable[[str], str]
OutputWriter = Callable[[str], None]


@dataclass(frozen=True)
class EnemyChoice:
    index: int
    unit_id: str
    label: str


@dataclass(frozen=True)
class AllyChoice:
    index: int
    unit_id: str
    label: str


def living_enemy_choices(state: BattleState, actor: CombatantState) -> list[EnemyChoice]:
    enemy_team = Team.ENEMY if actor.team == Team.PLAYER else Team.PLAYER
    targets = [unit for unit in state.combatants.values() if unit.team == enemy_team and unit.alive]
    targets.sort(key=lambda unit: unit.unit_id)
    return [
        EnemyChoice(index=index, unit_id=unit.unit_id, label=f"{unit.unit_id} hp={unit.hp}/{unit.max_hp}")
        for index, unit in enumerate(targets, start=1)
    ]


def _prompt_enemy_target(
    state: BattleState,
    actor: CombatantState,
    read_input: InputReader,
    write_output: OutputWriter,
) -> str:
    choices = living_enemy_choices(state, actor)
    if not choices:
        raise ValueError("対象となる生存ユニットが存在しません")

    write_output("target_required:単体対象のため敵を選択してください")
    for choice in choices:
        write_output(f"enemy_index:{choice.index}:{choice.label}")

    while True:
        raw = read_input("ターゲット番号> ").strip()
        if not raw.isdigit():
            write_output("target_input_invalid:数字を入力してください")
            continue
        selected = int(raw)
        matched = next((choice for choice in choices if choice.index == selected), None)
        if matched is None:
            write_output(f"target_input_invalid:範囲外です:{selected}")
            continue
        return matched.unit_id


def living_ally_choices(state: BattleState, actor: CombatantState) -> list[AllyChoice]:
    targets = [unit for unit in state.combatants.values() if unit.team == actor.team and unit.alive]
    targets.sort(key=lambda unit: unit.unit_id)
    return [
        AllyChoice(index=index, unit_id=unit.unit_id, label=f"{unit.unit_id} hp={unit.hp}/{unit.max_hp}")
        for index, unit in enumerate(targets, start=1)
    ]


def _prompt_ally_target(
    state: BattleState,
    actor: CombatantState,
    read_input: InputReader,
    write_output: OutputWriter,
) -> str:
    choices = living_ally_choices(state, actor)
    if not choices:
        raise ValueError("対象となる生存ユニットが存在しません")

    write_output("ally_target_required:味方単体対象のため味方を選択してください")
    for choice in choices:
        write_output(f"ally_index:{choice.index}:{choice.label}")

    while True:
        raw = read_input("味方ターゲット番号> ").strip()
        if not raw.isdigit():
            write_output("ally_target_input_invalid:数字を入力してください")
            continue
        selected = int(raw)
        matched = next((choice for choice in choices if choice.index == selected), None)
        if matched is None:
            write_output(f"ally_target_input_invalid:範囲外です:{selected}")
            continue
        return matched.unit_id


def choose_player_command(
    state: BattleState,
    actor: CombatantState,
    skills: dict[str, SkillDefinition],
    unit_skill_ids: tuple[str, ...],
    read_input: InputReader = input,
    write_output: OutputWriter = print,
) -> ActionCommand:
    if actor.team != Team.PLAYER:
        raise ValueError("choose_player_command はプレイヤー専用です")

    skill_choices = [skill_id for skill_id in unit_skill_ids if skill_id in skills]

    while True:
        write_output(f"actor:{actor.unit_id}:hp={actor.hp}/{actor.max_hp}:sp={actor.sp}")
        write_output("action_menu:1=attack 2=skill")
        action_raw = read_input("行動番号> ").strip()

        if action_raw == "1":
            target_id = _prompt_enemy_target(state, actor, read_input, write_output)
            return ActionCommand(actor_id=actor.unit_id, action_type="attack", target_id=target_id)

        if action_raw == "2":
            if not skill_choices:
                write_output("skill_unavailable:習得スキルがありません")
                continue

            write_output("skill_menu:使用するスキルを選択")
            for idx, skill_id in enumerate(skill_choices, start=1):
                skill = skills[skill_id]
                write_output(
                    f"skill_index:{idx}:{skill.id}:sp={skill.sp_cost}:scope={skill.target_scope}:power={skill.power}"
                )

            skill_raw = read_input("スキル番号> ").strip()
            if not skill_raw.isdigit():
                write_output("skill_input_invalid:数字を入力してください")
                continue
            skill_index = int(skill_raw)
            if skill_index < 1 or skill_index > len(skill_choices):
                write_output(f"skill_input_invalid:範囲外です:{skill_index}")
                continue

            skill_id = skill_choices[skill_index - 1]
            skill = skills[skill_id]
            if actor.sp < skill.sp_cost:
                write_output(f"skill_input_invalid:SP不足:{skill.id}")
                continue
            if skill.target_scope == "single_enemy":
                target_id = _prompt_enemy_target(state, actor, read_input, write_output)
            elif skill.target_scope == "all_enemies":
                target_id = None
                write_output("target_auto:全体対象のためターゲット選択は不要です")
            elif skill.target_scope == "single_ally":
                target_id = _prompt_ally_target(state, actor, read_input, write_output)
            elif skill.target_scope == "all_allies":
                target_id = None
                write_output("ally_target_auto:味方全体対象のためターゲット選択は不要です")
            else:
                raise ValueError(f"未対応のtarget_scopeです: {skill.target_scope}")
            return ActionCommand(actor_id=actor.unit_id, action_type="skill", skill_id=skill_id, target_id=target_id)

        write_output("action_input_invalid:1または2を入力してください")
