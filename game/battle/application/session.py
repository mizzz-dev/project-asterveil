from __future__ import annotations

from dataclasses import dataclass, field, replace

from game.battle.application.boss_phase import BossEncounterDefinition, BossPhaseService, BossPhaseState
from game.battle.application.enemy_ai import EnemyAiProfile, EnemyAiService
from game.battle.domain.entities import (
    ActionCommand,
    CombatantState,
    SkillDefinition,
    StatusEffectDefinition,
    Team,
    UnitDefinition,
)
from game.battle.domain.services import BattleState, execute_turn


@dataclass
class BattleSession:
    state: BattleState
    skills: dict[str, SkillDefinition]
    effect_definitions: dict[str, StatusEffectDefinition]
    enemy_ai_service: EnemyAiService = field(default_factory=EnemyAiService)
    enemy_ai_profiles: dict[str, EnemyAiProfile] = field(default_factory=dict)
    enemy_ai_by_enemy_id: dict[str, str] = field(default_factory=dict)
    runtime_enemy_map: dict[str, str] = field(default_factory=dict)
    encounter_id: str | None = None
    boss_encounters: dict[str, BossEncounterDefinition] = field(default_factory=dict)
    boss_phase_service: BossPhaseService = field(default_factory=BossPhaseService)
    boss_phase_states: dict[str, BossPhaseState] = field(default_factory=dict)

    @classmethod
    def from_definitions(
        cls,
        player_units: list[UnitDefinition],
        enemy_units: list[UnitDefinition],
        skills: dict[str, SkillDefinition],
        effect_definitions: dict[str, StatusEffectDefinition] | None = None,
    ) -> "BattleSession":
        combatants: dict[str, CombatantState] = {}
        for unit in [*player_units, *enemy_units]:
            combatants[unit.id] = CombatantState(
                unit_id=unit.id,
                team=unit.team,
                max_hp=unit.stats.hp,
                hp=unit.stats.hp,
                atk=unit.stats.atk,
                defense=unit.stats.defense,
                spd=unit.stats.spd,
                sp=100,
            )

        return cls(state=BattleState(combatants), skills=skills, effect_definitions=effect_definitions or {})

    @classmethod
    def create(
        cls,
        player_units: list[UnitDefinition],
        enemy_units: list[UnitDefinition],
        skills: dict[str, SkillDefinition],
        effect_definitions: dict[str, StatusEffectDefinition] | None = None,
        enemy_ai_profiles: dict[str, EnemyAiProfile] | None = None,
        enemy_ai_by_enemy_id: dict[str, str] | None = None,
        runtime_enemy_map: dict[str, str] | None = None,
        enemy_ai_service: EnemyAiService | None = None,
        encounter_id: str | None = None,
        boss_encounters: dict[str, BossEncounterDefinition] | None = None,
    ) -> "BattleSession":
        session = cls.from_definitions(player_units, enemy_units, skills, effect_definitions)
        session.enemy_ai_service = enemy_ai_service or EnemyAiService()
        session.enemy_ai_profiles = enemy_ai_profiles or {}
        session.enemy_ai_by_enemy_id = enemy_ai_by_enemy_id or {}
        session.runtime_enemy_map = runtime_enemy_map or {}
        session.encounter_id = encounter_id
        session.boss_encounters = boss_encounters or {}
        return session

    def default_command_factory(self, state: BattleState, actor: CombatantState) -> ActionCommand:
        if actor.team == Team.ENEMY:
            source_enemy_id = self.runtime_enemy_map.get(actor.unit_id, actor.unit_id)
            ai_profile_id = self.enemy_ai_by_enemy_id.get(source_enemy_id)
            phase_logs: tuple[str, ...] = tuple()

            encounter = self.boss_encounters.get(self.encounter_id or "")
            if encounter is not None and encounter.boss_enemy_id == source_enemy_id:
                runtime_state = self.boss_phase_states.get(actor.unit_id)
                if runtime_state is None:
                    runtime_state = self.boss_phase_service.initial_state(encounter)
                    self.boss_phase_states[actor.unit_id] = runtime_state
                phase_result = self.boss_phase_service.resolve_phase(
                    state,
                    actor,
                    encounter,
                    runtime_state,
                    self.effect_definitions,
                )
                phase_logs = phase_result.logs
                if phase_result.active_phase.ai_profile_id:
                    ai_profile_id = phase_result.active_phase.ai_profile_id

            ai_profile = self.enemy_ai_profiles.get(ai_profile_id) if ai_profile_id else None
            command = self.enemy_ai_service.choose_command(state, actor, ai_profile, self.skills)
            return replace(command, logs=tuple([*phase_logs, *command.logs]))

        enemy_team = Team.ENEMY if actor.team == Team.PLAYER else Team.PLAYER
        enemy_targets = [c for c in state.combatants.values() if c.team == enemy_team and c.alive]
        enemy_targets.sort(key=lambda c: c.unit_id)
        ally_targets = [c for c in state.combatants.values() if c.team == actor.team and c.alive]
        ally_targets.sort(key=lambda c: c.unit_id)
        target = enemy_targets[0]

        unit_skill_ids = self._unit_skill_ids(actor.unit_id)
        if unit_skill_ids:
            skill_id = unit_skill_ids[0]
            skill = self.skills[skill_id]
            if actor.sp >= skill.sp_cost:
                if skill.target_scope in ("all_enemies", "all_allies"):
                    target_id = None
                elif skill.target_scope == "single_ally":
                    target_id = actor.unit_id
                    wounded = [ally for ally in ally_targets if ally.hp < ally.max_hp]
                    if wounded:
                        target_id = wounded[0].unit_id
                else:
                    target_id = target.unit_id
                return ActionCommand(
                    actor_id=actor.unit_id,
                    action_type="skill",
                    target_id=target_id,
                    skill_id=skill_id,
                )

        return ActionCommand(
            actor_id=actor.unit_id,
            action_type="attack",
            target_id=target.unit_id,
        )

    def _unit_skill_ids(self, unit_id: str) -> tuple[str, ...]:
        unit = getattr(self, "_unit_skills_cache", {}).get(unit_id)
        if unit is not None:
            return unit
        return tuple()

    def unit_skill_ids(self, unit_id: str) -> tuple[str, ...]:
        return self._unit_skill_ids(unit_id)

    def bind_unit_skills(self, unit_skills: dict[str, tuple[str, ...]]) -> None:
        self._unit_skills_cache = unit_skills

    def step_round(self) -> list:
        results = []
        for actor_id in self.state.turn_order():
            turn = execute_turn(
                state=self.state,
                actor_id=actor_id,
                command_factory=self.default_command_factory,
                skills=self.skills,
                effect_definitions=self.effect_definitions,
            )
            if turn.acted:
                results.append(turn)
            if turn.winner is not None:
                break
        return results

    def run_until_finished(self, max_rounds: int = 20) -> Team | None:
        for _ in range(max_rounds):
            if self.state.is_finished():
                return self.state.winner()
            self.step_round()
        return self.state.winner()
