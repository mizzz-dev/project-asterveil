from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.dialogue_event_service import DialogueService, LocationEventService
from game.app.application.playable_slice import PlayableSliceApplication
from game.app.infrastructure.dialogue_event_repository import DialogueEventMasterDataRepository
from game.quest.domain.entities import BattleResult, QuestState, QuestStatus


class DialogueEventSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = DialogueEventMasterDataRepository(Path("data/master"))

    def test_load_npc_dialogues(self) -> None:
        definitions = self.repository.load_npc_dialogues()
        self.assertIn("npc.astel.elder", definitions)
        self.assertGreaterEqual(len(definitions["npc.astel.elder"].dialogue_entries), 1)

    def test_dialogue_changes_by_quest_status_and_flags(self) -> None:
        service = DialogueService(self.repository.load_npc_dialogues())
        world_flags = {"flag.game.new_game_started", "flag.quest.accepted:quest.ch01.missing_port_record"}
        quest_states = {
            "quest.ch01.missing_port_record": QuestState(
                quest_id="quest.ch01.missing_port_record",
                status=QuestStatus.IN_PROGRESS,
            )
        }
        in_progress = service.resolve("npc.astel.elder", "location.town.astel", world_flags, quest_states)
        self.assertTrue(any("準備" in line for line in in_progress.lines))

        quest_states["quest.ch01.missing_port_record"].status = QuestStatus.COMPLETED
        world_flags.add("flag.ch01.tidal_flats_intro_seen")
        completed = service.resolve("npc.astel.elder", "location.town.astel", world_flags, quest_states)
        self.assertTrue(any("落ち着き" in line for line in completed.lines))

    def test_dialogue_failure_when_npc_unknown(self) -> None:
        service = DialogueService(self.repository.load_npc_dialogues())
        result = service.resolve("npc.unknown", "location.town.astel", set(), {})
        self.assertFalse(result.success)
        self.assertEqual(result.code, "npc_not_found")

    def test_location_event_trigger_and_repeat_prevention(self) -> None:
        service = LocationEventService(self.repository.load_location_events())
        quest_states = {
            "quest.ch01.missing_port_record": QuestState(
                quest_id="quest.ch01.missing_port_record",
                status=QuestStatus.IN_PROGRESS,
            )
        }
        first = service.resolve_on_enter(
            "location.field.tidal_flats",
            world_flags=set(),
            quest_states=quest_states,
            completed_event_ids=set(),
        )
        self.assertEqual(len(first), 1)

        second = service.resolve_on_enter(
            "location.field.tidal_flats",
            world_flags={"flag.ch01.tidal_flats_intro_seen"},
            quest_states=quest_states,
            completed_event_ids={"event.location.tidal_flats.first_entry"},
        )
        self.assertEqual(second, [])

    def test_playable_integration_event_battle_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            def battle_executor(encounter_id: str) -> BattleResult:
                return BattleResult(
                    encounter_id=encounter_id,
                    player_won=True,
                    defeated_enemy_ids=("enemy.ch01.port_wraith",),
                )

            app = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            travel_logs = app.travel_to("location.field.tidal_flats")
            self.assertIn("location_event_started:event.location.tidal_flats.first_entry", travel_logs)
            self.assertIn("flag_set:flag.ch01.tidal_flats_intro_seen", travel_logs)
            self.assertTrue(any(line.startswith("battle_finished:encounter.ch01.port_wraith") for line in travel_logs))

            repeat_logs = app.travel_to("location.town.astel") + app.travel_to("location.field.tidal_flats")
            self.assertFalse(any("location_event_started:event.location.tidal_flats.first_entry" == line for line in repeat_logs))

            app.perform_action("save")
            resumed = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            resumed.continue_game()
            self.assertIn("event.location.tidal_flats.first_entry", resumed.completed_location_event_ids)
            resumed.travel_to("location.town.astel")
            dialogue_logs = resumed.talk_to_npc("npc.astel.guard")
            self.assertTrue(any("もう出ていない" in line for line in dialogue_logs))


if __name__ == "__main__":
    unittest.main()
