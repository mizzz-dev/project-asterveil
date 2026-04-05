from __future__ import annotations

import unittest
from pathlib import Path

from game.app.application.reward_services import RewardApplicationService, RewardBundle
from game.app.application.skill_learning_service import LearnableSkill, SkillLearningService
from game.app.infrastructure.master_data_repository import AppMasterDataRepository
from game.battle.application.session import BattleSession
from game.battle.infrastructure.master_data_repository import MasterDataRepository
from game.save.domain.entities import PartyMemberState, SaveData


class SkillLearningSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.master_root = Path("data/master")
        self.app_repo = AppMasterDataRepository(self.master_root)
        self.battle_repo = MasterDataRepository(self.master_root)
        self.skill_learning = SkillLearningService(
            learnable_by_character={
                character_id: tuple(
                    LearnableSkill(
                        skill_id=entry["skill_id"],
                        required_level=entry["required_level"],
                        learn_type=entry.get("learn_type", "auto"),
                        description=entry.get("description", ""),
                    )
                    for entry in entries
                )
                for character_id, entries in self.app_repo.load_skill_learns().items()
            },
            initial_skill_ids_by_character=self.app_repo.load_initial_skill_ids_by_character(),
        )

    def _member(self, level: int = 8) -> PartyMemberState:
        return PartyMemberState(
            character_id="char.main.rion",
            level=level,
            current_exp=0,
            next_level_exp=450,
            max_hp=120,
            current_hp=120,
            max_sp=100,
            current_sp=100,
            atk=24,
            defense=16,
            spd=18,
            alive=True,
            unlocked_skill_ids=[],
        )

    def test_load_skill_learn_definitions(self) -> None:
        loaded = self.app_repo.load_skill_learns()
        self.assertIn("char.main.rion", loaded)
        self.assertEqual(loaded["char.main.rion"][0]["skill_id"], "skill.striker.venom_edge")
        self.assertEqual(loaded["char.main.rion"][1]["required_level"], 10)

    def test_initial_skills_and_level_up_learning_with_duplicate_protection(self) -> None:
        member = self._member(level=8)
        initial_logs = self.skill_learning.apply_initial_skills(member)
        self.assertIn("skill.striker.flare_slash", member.unlocked_skill_ids)
        self.assertEqual(len(initial_logs), 1)

        member.level = 10
        learned_logs = self.skill_learning.apply_level_up_skills(member, previous_level=8)
        self.assertIn("skill.striker.venom_edge", member.unlocked_skill_ids)
        self.assertIn("skill.striker.guard_break", member.unlocked_skill_ids)
        self.assertEqual(len(learned_logs), 2)

        duplicate_logs = self.skill_learning.apply_level_up_skills(member, previous_level=9)
        self.assertEqual(duplicate_logs, [])

    def test_reward_service_emits_learn_logs(self) -> None:
        member = self._member(level=8)
        self.skill_learning.apply_initial_skills(member)
        service = RewardApplicationService(skill_learning=self.skill_learning)
        logs = service.apply(RewardBundle(exp=500), [member], {"gold": 0, "items": {}})
        self.assertTrue(any(log.startswith("learned_skill:char.main.rion:skill.striker.venom_edge") for log in logs))

    def test_battle_uses_only_learned_skills(self) -> None:
        base_player = self.battle_repo.load_character("char.main.rion")
        enemy = self.battle_repo.load_enemy("enemy.ch01.port_wraith")
        skills = self.battle_repo.load_skills()
        effects = self.battle_repo.load_status_effects()

        no_skill_player = base_player.__class__(
            id=base_player.id,
            team=base_player.team,
            stats=base_player.stats,
            skill_ids=tuple(),
        )
        session = BattleSession.from_definitions([no_skill_player], [enemy], skills, effects)
        session.bind_unit_skills({no_skill_player.id: tuple(), enemy.id: enemy.skill_ids})
        actor = session.state.combatants[no_skill_player.id]
        command = session.default_command_factory(session.state, actor)
        self.assertEqual(command.action_type, "attack")

        learned_player = base_player.__class__(
            id=base_player.id,
            team=base_player.team,
            stats=base_player.stats,
            skill_ids=("skill.striker.venom_edge",),
        )
        learned_session = BattleSession.from_definitions([learned_player], [enemy], skills, effects)
        learned_session.bind_unit_skills({learned_player.id: learned_player.skill_ids, enemy.id: enemy.skill_ids})
        learned_actor = learned_session.state.combatants[learned_player.id]
        learned_command = learned_session.default_command_factory(learned_session.state, learned_actor)
        self.assertEqual(learned_command.action_type, "skill")
        self.assertEqual(learned_command.skill_id, "skill.striker.venom_edge")

    def test_save_load_preserves_learned_skills(self) -> None:
        raw = {
            "save_version": 1,
            "player_profile": {
                "difficulty": "standard",
                "play_time_sec": 12,
                "last_saved_at": "2026-04-05T00:00:00+00:00",
            },
            "party_state": {
                "members": [
                    {
                        "character_id": "char.main.rion",
                        "level": 10,
                        "current_exp": 0,
                        "next_level_exp": 550,
                        "current_hp": 100,
                        "current_sp": 80,
                        "alive": True,
                        "unlocked_skill_ids": [
                            "skill.striker.flare_slash",
                            "skill.striker.venom_edge",
                            "skill.striker.guard_break",
                        ],
                    }
                ]
            },
            "quest_state": {},
            "world_flags": {},
        }
        save_data = SaveData.from_dict(raw)
        self.assertEqual(
            save_data.party_members[0].unlocked_skill_ids,
            ["skill.striker.flare_slash", "skill.striker.venom_edge", "skill.striker.guard_break"],
        )


if __name__ == "__main__":
    unittest.main()
