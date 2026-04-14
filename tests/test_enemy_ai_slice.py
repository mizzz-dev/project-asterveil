from __future__ import annotations

import random
import unittest
from pathlib import Path

from game.battle.application.enemy_ai import EnemyAiService
from game.battle.application.session import BattleSession
from game.battle.domain.entities import ActiveEffectState, Team
from game.battle.domain.services import execute_turn
from game.battle.infrastructure.master_data_repository import MasterDataRepository


class EnemyAiSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = MasterDataRepository(Path("data/master"))
        self.skills = self.repo.load_skills()
        self.effects = self.repo.load_status_effects()
        self.player = self.repo.load_character("char.main.rion")
        self.ai_profiles = self.repo.load_enemy_ai_profiles()
        self.ai_bindings = self.repo.load_enemy_ai_bindings()

    def _session(self, encounter_id: str = "encounter.ch01.harbor_miasma_patrol") -> BattleSession:
        enemies, runtime_enemy_map = self.repo.build_enemy_party(encounter_id)
        session = BattleSession.create(
            [self.player],
            enemies,
            self.skills,
            self.effects,
            enemy_ai_profiles=self.ai_profiles,
            enemy_ai_by_enemy_id=self.ai_bindings,
            runtime_enemy_map=runtime_enemy_map,
            enemy_ai_service=EnemyAiService(random.Random(0)),
        )
        session.bind_unit_skills(
            {
                self.player.id: self.player.skill_ids,
                **{enemy.id: enemy.skill_ids for enemy in enemies},
            }
        )
        return session

    def test_load_enemy_ai_profile(self) -> None:
        self.assertIn("enemy_ai.port_wraith.poison_heal", self.ai_profiles)
        self.assertEqual(self.ai_bindings["enemy.ch01.brine_slime"], "enemy_ai.brine_slime.debuff")

    def test_enemy_uses_poison_skill_when_target_has_no_poison(self) -> None:
        session = self._session("encounter.ch01.harbor_miasma_patrol")
        enemy_id = next(
            unit.unit_id for unit in session.state.combatants.values() if unit.team == Team.ENEMY and "port_wraith" in unit.unit_id
        )
        enemy_actor = session.state.combatants[enemy_id]
        command = session.default_command_factory(session.state, enemy_actor)
        self.assertEqual(command.action_type, "skill")
        self.assertEqual(command.skill_id, "skill.enemy.venom_bite")
        self.assertTrue(any("selected_rule=rule.port_wraith.apply_poison" in log for log in command.logs))

    def test_enemy_avoids_poison_overlap_and_fallbacks_to_attack(self) -> None:
        session = self._session("encounter.ch01.harbor_miasma_patrol")
        enemy_id = next(
            unit.unit_id for unit in session.state.combatants.values() if unit.team == Team.ENEMY and "port_wraith" in unit.unit_id
        )
        enemy_actor = session.state.combatants[enemy_id]
        player_actor = session.state.combatants[self.player.id]
        player_actor.active_effects.append(ActiveEffectState(effect_id="effect.ailment.poison", remaining_turns=2))

        command = session.default_command_factory(session.state, enemy_actor)
        self.assertEqual(command.action_type, "attack")

    def test_enemy_heals_lowest_hp_ally_when_low_hp_exists(self) -> None:
        session = self._session()
        enemies = [unit for unit in session.state.combatants.values() if unit.team == Team.ENEMY]
        wraith = next(unit for unit in enemies if "port_wraith" in unit.unit_id)
        target_ally = next(unit for unit in enemies if unit.unit_id != wraith.unit_id)
        target_ally.hp = max(1, int(target_ally.max_hp * 0.3))

        command = session.default_command_factory(session.state, wraith)
        self.assertEqual(command.action_type, "skill")
        self.assertEqual(command.skill_id, "skill.enemy.shadow_mend")
        self.assertEqual(command.target_id, target_ally.unit_id)

    def test_enemy_debuffs_then_attacks_after_overlap(self) -> None:
        session = self._session()
        slime = next(unit for unit in session.state.combatants.values() if "brine_slime#1" in unit.unit_id)
        player = session.state.combatants[self.player.id]

        first = session.default_command_factory(session.state, slime)
        self.assertEqual(first.skill_id, "skill.enemy.armor_crush")
        execute_turn(session.state, slime.unit_id, lambda *_: first, session.skills, session.effect_definitions)
        second = session.default_command_factory(session.state, slime)
        self.assertEqual(second.action_type, "attack")
        self.assertTrue(any(effect.effect_id == "effect.debuff.defense_down" for effect in player.active_effects))

    def test_enemy_ai_log_is_recorded_in_turn_result(self) -> None:
        session = self._session("encounter.ch01.port_wraith_single")
        enemy_id = next(unit.unit_id for unit in session.state.combatants.values() if unit.team == Team.ENEMY)
        turn = execute_turn(
            session.state,
            enemy_id,
            session.default_command_factory,
            session.skills,
            session.effect_definitions,
        )
        self.assertTrue(any(log.startswith("enemy_ai:selected_rule=") for log in turn.logs))


if __name__ == "__main__":
    unittest.main()
