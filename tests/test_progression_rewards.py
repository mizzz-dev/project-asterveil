from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from game.app.application.reward_services import ProgressionService, RewardApplicationService, RewardBundle, RewardItem
from game.app.infrastructure.master_data_repository import AppMasterDataRepository
from game.save.domain.entities import PartyMemberState


class ProgressionRewardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.progression = ProgressionService()
        self.reward_service = RewardApplicationService(self.progression)
        self.member = PartyMemberState(
            character_id="char.main.rion",
            level=1,
            next_level_exp=100,
            max_hp=120,
            current_hp=120,
            max_sp=100,
            current_sp=100,
            atk=20,
            defense=12,
            spd=10,
            alive=True,
        )

    def test_apply_battle_reward_updates_exp_gold_and_items(self) -> None:
        inventory = {"gold": 10, "items": {}}
        logs = self.reward_service.apply(
            RewardBundle(
                exp=220,
                gold=35,
                items=(RewardItem("item.material.memory_shard", 2),),
            ),
            [self.member],
            inventory,
        )
        self.assertGreaterEqual(self.member.level, 2)
        self.assertEqual(inventory["gold"], 45)
        self.assertEqual(inventory["items"]["item.material.memory_shard"], 2)
        self.assertTrue(any(log.startswith("exp_applied:") for log in logs))

    def test_level_up_raises_stats(self) -> None:
        level_ups = self.progression.grant_exp(self.member, 100)
        self.assertEqual(level_ups, 1)
        self.assertEqual(self.member.level, 2)
        self.assertEqual(self.member.max_hp, 132)
        self.assertEqual(self.member.atk, 22)

    def test_invalid_reward_data_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "items.sample.json").write_text(
                json.dumps([{"id": "item.material.memory_shard", "category": "material", "name": "記憶片"}]),
                encoding="utf-8",
            )
            (root / "reward_tables.sample.json").write_text(
                json.dumps(
                    {
                        "battle_rewards": [
                            {
                                "encounter_id": "encounter.invalid",
                                "items": [{"item_id": "item.unknown", "amount": 1}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            repo = AppMasterDataRepository(root)
            items = repo.load_items()
            with self.assertRaises(ValueError):
                repo.load_battle_rewards(set(items))


if __name__ == "__main__":
    unittest.main()
