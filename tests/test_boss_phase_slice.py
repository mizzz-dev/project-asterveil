from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.battle.application.enemy_ai import EnemyAiService
from game.battle.application.session import BattleSession
from game.battle.infrastructure.master_data_repository import MasterDataRepository
from game.quest.domain.entities import BattleResult, QuestStatus


class BossPhaseSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = MasterDataRepository(Path("data/master"))
        self.skills = self.repo.load_skills()
        self.effects = self.repo.load_status_effects()
        self.ai_profiles = self.repo.load_enemy_ai_profiles()
        self.ai_bindings = self.repo.load_enemy_ai_bindings()
        self.boss_defs = self.repo.load_boss_encounters()
        self.player = self.repo.load_character("char.main.rion")

    def _boss_session(self) -> BattleSession:
        encounter_id = "encounter.ch01.tide_serpent_boss"
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
            encounter_id=encounter_id,
            boss_encounters=self.boss_defs,
        )
        session.bind_unit_skills(
            {
                self.player.id: self.player.skill_ids,
                **{enemy.id: enemy.skill_ids for enemy in enemies},
            }
        )
        return session

    def test_load_boss_encounter_definition(self) -> None:
        self.assertIn("encounter.ch01.tide_serpent_boss", self.boss_defs)
        definition = self.boss_defs["encounter.ch01.tide_serpent_boss"]
        self.assertEqual(definition.boss_enemy_id, "enemy.ch01.tide_serpent")
        self.assertEqual(len(definition.phases), 2)
        self.assertEqual(definition.phases[1].enter_condition.condition_type, "hp_ratio_below")

    def test_boss_phase_transition_switches_ai_and_runs_on_enter_once(self) -> None:
        session = self._boss_session()
        boss = next(unit for unit in session.state.combatants.values() if unit.team.value == "enemy")

        opening = session.default_command_factory(session.state, boss)
        self.assertEqual(opening.action_type, "skill")
        self.assertEqual(opening.skill_id, "skill.enemy.venom_bite")
        self.assertTrue(any("boss_phase_active" in log for log in opening.logs))
        self.assertFalse(any("boss_phase_transition" in log for log in opening.logs))

        boss.hp = int(boss.max_hp * 0.5)
        phase2 = session.default_command_factory(session.state, boss)
        self.assertEqual(phase2.action_type, "skill")
        self.assertEqual(phase2.skill_id, "skill.enemy.tide_roar")
        self.assertTrue(any("boss_phase_transition" in log for log in phase2.logs))
        self.assertTrue(any("boss_phase_message" in log for log in phase2.logs))
        self.assertTrue(any("boss_phase_effect_applied" in log for log in phase2.logs))
        self.assertTrue(any(effect.effect_id == "effect.buff.attack_up" for effect in boss.active_effects))

        again = session.default_command_factory(session.state, boss)
        self.assertEqual(again.skill_id, "skill.enemy.tide_roar")
        self.assertFalse(any("boss_phase_transition" in log for log in again.logs))
        self.assertTrue(any("selected_rule=rule.tide_serpent.phase2.tide_roar" in log for log in again.logs))

    def test_boss_quest_loop_updates_progress_and_persists_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            def battle_executor(encounter_id: str, *_args) -> BattleResult:
                self.assertEqual(encounter_id, "encounter.ch01.tide_serpent_boss")
                return BattleResult(
                    encounter_id=encounter_id,
                    player_won=True,
                    defeated_enemy_ids=("enemy.ch01.tide_serpent",),
                )

            app = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            app.new_game()

            cleanup_state = app.quest_session.quest_service.create_initial_state("quest.ch01.harbor_cleanup")
            cleanup_state.status = QuestStatus.COMPLETED
            app.quest_session.quest_states[cleanup_state.quest_id] = cleanup_state
            app.quest_session.world_flags.add("flag.ch01.harbor_secured")
            app.location_state.unlocked_location_ids.add("location.dungeon.tidegate_ruins")

            self.assertEqual(
                app.accept_quest("quest.ch01.tide_serpent_subjugation"),
                ["quest_accepted:quest.ch01.tide_serpent_subjugation"],
            )
            app.travel_to("location.dungeon.tidegate_ruins")
            hunt_logs = app.perform_action("hunt")
            self.assertTrue(any("battle_finished:encounter.ch01.tide_serpent_boss:player_won=True" in log for log in hunt_logs))
            self.assertTrue(
                any("quest_status_changed:quest.ch01.tide_serpent_subjugation:ready_to_complete" in log for log in hunt_logs)
            )

            report_logs = app.perform_action("report")
            self.assertTrue(any("quest_completed:quest.ch01.tide_serpent_subjugation" in log for log in report_logs))
            self.assertIn("flag.ch01.tide_serpent_subjugated", app.quest_session.world_flags)

            app.perform_action("save")
            resumed = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            self.assertEqual(resumed.quest_state("quest.ch01.tide_serpent_subjugation").status, QuestStatus.COMPLETED)
            self.assertIn("flag.ch01.tide_serpent_subjugated", resumed.quest_session.world_flags)


if __name__ == "__main__":
    unittest.main()
