from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from game.quest.application.session import QuestSliceSession
from game.quest.domain.entities import BattleResult, QuestStatus
from game.quest.domain.services import QuestProgressService
from game.quest.infrastructure.master_data_repository import QuestMasterDataRepository


class QuestSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = QuestMasterDataRepository(Path("data/master"))
        self.quest_defs = self.repo.load_quests()
        self.event_defs = self.repo.load_events()

    def test_event_data_loading(self) -> None:
        self.assertIn("event.ch01.port_request", self.event_defs)
        self.assertGreaterEqual(len(self.event_defs["event.ch01.port_request"].steps), 3)

    def test_accept_and_complete_flow_with_battle_win(self) -> None:
        def battle_executor(encounter_id: str) -> BattleResult:
            self.assertEqual(encounter_id, "encounter.ch01.port_wraith")
            return BattleResult(
                encounter_id=encounter_id,
                player_won=True,
                defeated_enemy_ids=("enemy.ch01.port_wraith",),
            )

        session = QuestSliceSession(
            quest_service=QuestProgressService(self.quest_defs),
            events=self.event_defs,
            battle_executor=battle_executor,
        )

        session.play_event("event.ch01.port_request")
        quest_state = session.quest_states["quest.ch01.missing_port_record"]
        self.assertEqual(quest_state.status, QuestStatus.READY_TO_COMPLETE)

        session.play_event("event.ch01.port_report")
        self.assertEqual(quest_state.status, QuestStatus.COMPLETED)
        self.assertTrue(quest_state.reward_claimed)
        self.assertIn("flag.ch01.port_record_restored", session.world_flags)

    def test_battle_loss_keeps_quest_in_progress(self) -> None:
        session = QuestSliceSession(
            quest_service=QuestProgressService(self.quest_defs),
            events=self.event_defs,
            battle_executor=lambda encounter_id: BattleResult(
                encounter_id=encounter_id,
                player_won=False,
                defeated_enemy_ids=tuple(),
            ),
        )

        session.play_event("event.ch01.port_request")
        quest_state = session.quest_states["quest.ch01.missing_port_record"]
        self.assertEqual(quest_state.status, QuestStatus.IN_PROGRESS)
        self.assertFalse(quest_state.reward_claimed)

    def test_invalid_quest_data_detected(self) -> None:
        broken_quests = [
            {
                "id": "quest.invalid.sample",
                "title": "invalid",
                "description": "missing objectives",
                "reward": {"exp": 1, "gold": 1},
            }
        ]
        events = [
            {
                "id": "event.valid.sample",
                "title": "valid",
                "steps": [{"id": "step_001"}],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "quests.sample.json").write_text(json.dumps(broken_quests), encoding="utf-8")
            (root / "events.sample.json").write_text(json.dumps(events), encoding="utf-8")

            repo = QuestMasterDataRepository(root)
            with self.assertRaises(ValueError):
                repo.load_quests()


if __name__ == "__main__":
    unittest.main()
