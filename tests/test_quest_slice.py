from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from game.quest.application.session import QuestSliceSession
from game.quest.domain.entities import BattleResult, QuestStatus
from game.quest.domain.services import QuestBoardService, QuestProgressService
from game.quest.infrastructure.master_data_repository import QuestMasterDataRepository


class QuestSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = QuestMasterDataRepository(Path("data/master"))
        self.quest_defs = self.repo.load_quests()
        self.event_defs = self.repo.load_events()

    def test_event_data_loading(self) -> None:
        self.assertIn("event.ch01.port_request", self.event_defs)
        self.assertGreaterEqual(len(self.event_defs["event.ch01.port_request"].steps), 3)
        self.assertGreaterEqual(len(self.quest_defs), 3)

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

    def test_quest_board_unlock_conditions_and_accept_limit(self) -> None:
        board = QuestBoardService(self.quest_defs, max_active_quests=1)
        quest_states = {}
        world_flags = {"flag.game.new_game_started"}

        entries = {entry.quest_id: entry for entry in board.list_entries(quest_states, world_flags, party_level=1)}
        self.assertEqual(entries["quest.ch01.missing_port_record"].status.value, "available")
        self.assertEqual(entries["quest.ch01.harbor_cleanup"].status.value, "locked")
        self.assertEqual(entries["quest.ch01.rookie_level_trial"].status.value, "locked")

        quest_states["quest.ch01.missing_port_record"] = QuestProgressService(self.quest_defs).accept(
            QuestProgressService(self.quest_defs).create_initial_state("quest.ch01.missing_port_record")
        )
        self.assertFalse(board.can_accept_more(quest_states))

        quest_states["quest.ch01.missing_port_record"].status = QuestStatus.COMPLETED
        entries = {entry.quest_id: entry for entry in board.list_entries(quest_states, world_flags, party_level=8)}
        self.assertEqual(entries["quest.ch01.harbor_cleanup"].status.value, "available")
        self.assertEqual(entries["quest.ch01.rookie_level_trial"].status.value, "available")

    def test_turn_in_objective_loading_and_progress(self) -> None:
        quest_id = "quest.ch01.herb_supply_turn_in"
        definition = self.quest_defs[quest_id]
        objective = definition.objectives[0]
        self.assertEqual(objective.objective_type, "turn_in_items")
        self.assertEqual(objective.required_items, (("item.consumable.antidote_leaf", 1),))

        service = QuestProgressService(self.quest_defs)
        state = service.accept(service.create_initial_state(quest_id))

        insufficient = service.build_turn_in_plan(state, {"item.consumable.antidote_leaf": 0})
        self.assertFalse(insufficient.success)
        self.assertEqual(insufficient.code, "turn_in_failed:insufficient_items")

        inventory_state = {"items": {"item.consumable.antidote_leaf": 2}}
        plan = service.build_turn_in_plan(state, inventory_state["items"])
        self.assertTrue(plan.success)
        service.consume_turn_in_items(inventory_state, plan)
        logs = service.apply_turn_in_progress(state, plan)
        self.assertIn("turn_in_success:quest.ch01.herb_supply_turn_in:obj.ch01.turn_in_antidote_leaf:item.consumable.antidote_leaf:submitted=1/1:delta=1", logs)
        self.assertEqual(inventory_state["items"]["item.consumable.antidote_leaf"], 1)
        self.assertEqual(state.status, QuestStatus.READY_TO_COMPLETE)

    def test_repeatable_quest_reset_rule_and_reaccept(self) -> None:
        service = QuestProgressService(self.quest_defs)

        herb_state = service.accept(service.create_initial_state("quest.ch01.herb_supply_turn_in"))
        herb_state.objective_progress["obj.ch01.turn_in_antidote_leaf"] = 1
        herb_state.status = QuestStatus.READY_TO_COMPLETE
        service.complete(herb_state)

        self.assertFalse(herb_state.repeat_ready)
        self.assertFalse(service.apply_repeat_reset_trigger(herb_state, "on_return_to_hub"))
        self.assertTrue(service.apply_repeat_reset_trigger(herb_state, "on_rest"))
        self.assertTrue(herb_state.repeat_ready)

        herb_state.objective_item_progress["obj.ch01.turn_in_antidote_leaf"]["item.consumable.antidote_leaf"] = 1
        service.reaccept(herb_state)
        self.assertEqual(herb_state.status, QuestStatus.IN_PROGRESS)
        self.assertEqual(herb_state.objective_progress["obj.ch01.turn_in_antidote_leaf"], 0)
        self.assertEqual(
            herb_state.objective_item_progress["obj.ch01.turn_in_antidote_leaf"]["item.consumable.antidote_leaf"],
            0,
        )

    def test_quest_board_status_for_repeatable_quest(self) -> None:
        board = QuestBoardService(self.quest_defs, max_active_quests=2)
        states = {}
        world_flags = {"flag.game.new_game_started", "flag.ch01.port_record_restored"}
        service = QuestProgressService(self.quest_defs)

        harbor = service.accept(service.create_initial_state("quest.ch01.harbor_cleanup"))
        harbor.status = QuestStatus.READY_TO_COMPLETE
        service.complete(harbor)
        states["quest.ch01.harbor_cleanup"] = harbor

        entries = {entry.quest_id: entry for entry in board.list_entries(states, world_flags, party_level=8)}
        self.assertEqual(entries["quest.ch01.harbor_cleanup"].status.value, "repost_waiting")
        self.assertFalse(entries["quest.ch01.harbor_cleanup"].can_accept)

        service.apply_repeat_reset_trigger(harbor, "on_return_to_hub")
        entries = {entry.quest_id: entry for entry in board.list_entries(states, world_flags, party_level=8)}
        self.assertEqual(entries["quest.ch01.harbor_cleanup"].status.value, "reacceptable")
        self.assertTrue(entries["quest.ch01.harbor_cleanup"].can_accept)


if __name__ == "__main__":
    unittest.main()
