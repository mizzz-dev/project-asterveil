from __future__ import annotations

import unittest
from pathlib import Path

from game.battle.application.command_selection import choose_player_command, living_enemy_choices
from game.battle.application.session import BattleSession
from game.battle.domain.entities import Team
from game.battle.infrastructure.master_data_repository import MasterDataRepository


class BattleTargetSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = MasterDataRepository(Path("data/master"))
        self.skills = self.repo.load_skills()
        self.effects = self.repo.load_status_effects()
        self.player = self.repo.load_character("char.main.rion")
        self.enemies, _ = self.repo.build_enemy_party("encounter.ch01.harbor_miasma_patrol")
        self.session = BattleSession.from_definitions([self.player], self.enemies, self.skills, self.effects)
        self.session.bind_unit_skills(
            {
                self.player.id: self.player.skill_ids,
                **{enemy.id: enemy.skill_ids for enemy in self.enemies},
            }
        )
        self.actor = self.session.state.combatants[self.player.id]

    def _reader(self, values: list[str]):
        data = iter(values)

        def _read(_: str) -> str:
            return next(data)

        return _read

    def test_living_enemy_choices_excludes_defeated(self) -> None:
        enemies = [c for c in self.session.state.combatants.values() if c.team == Team.ENEMY]
        enemies[0].apply_damage(9999)

        choices = living_enemy_choices(self.session.state, self.actor)
        self.assertEqual(len(choices), len(enemies) - 1)
        self.assertNotIn(enemies[0].unit_id, [choice.unit_id for choice in choices])

    def test_choose_attack_requires_target_selection(self) -> None:
        outputs: list[str] = []
        command = choose_player_command(
            state=self.session.state,
            actor=self.actor,
            skills=self.skills,
            unit_skill_ids=("skill.striker.flare_slash",),
            read_input=self._reader(["1", "2"]),
            write_output=outputs.append,
        )

        self.assertEqual(command.action_type, "attack")
        self.assertTrue(command.target_id)
        self.assertIn("target_required:単体対象のため敵を選択してください", outputs)

    def test_choose_all_enemy_skill_skips_target_prompt(self) -> None:
        outputs: list[str] = []
        command = choose_player_command(
            state=self.session.state,
            actor=self.actor,
            skills=self.skills,
            unit_skill_ids=("skill.striker.arc_wave",),
            read_input=self._reader(["2", "1"]),
            write_output=outputs.append,
        )

        self.assertEqual(command.action_type, "skill")
        self.assertEqual(command.skill_id, "skill.striker.arc_wave")
        self.assertIsNone(command.target_id)
        self.assertIn("target_auto:全体対象のためターゲット選択は不要です", outputs)


if __name__ == "__main__":
    unittest.main()
