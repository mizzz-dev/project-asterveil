from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.quest.domain.entities import BattleResult, QuestStatus


class PlayableSliceTests(unittest.TestCase):
    def _build_app(self, tmp_dir: str, *, win: bool = True) -> PlayableSliceApplication:
        def battle_executor(encounter_id: str) -> BattleResult:
            self.assertEqual(encounter_id, "encounter.ch01.port_wraith")
            return BattleResult(
                encounter_id=encounter_id,
                player_won=win,
                defeated_enemy_ids=("enemy.ch01.port_wraith",) if win else tuple(),
            )

        return PlayableSliceApplication(
            master_root=Path("data/master"),
            save_file_path=Path(tmp_dir) / "slot_01.json",
            battle_executor=battle_executor,
        )

    def test_new_game_creates_initial_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            logs = app.new_game()

            self.assertIn("new_game_started", logs)
            self.assertEqual(len(app.party_members), 1)
            self.assertEqual(app.last_event_id, "event.system.new_game_intro")
            self.assertIn("flag.game.new_game_started", app.quest_session.world_flags)
            self.assertEqual(app.inventory_state["gold"], 0)

    def test_continue_loads_saved_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.perform_action("talk_npc")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            ok, message = resumed.continue_game()

            self.assertTrue(ok)
            self.assertIn("ロード", message)
            self.assertEqual(resumed.quest_state().status, QuestStatus.READY_TO_COMPLETE)
            self.assertGreater(resumed.inventory_state["gold"], 0)

    def test_transition_from_in_progress_to_reportable_to_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            losing_app = self._build_app(tmp_dir, win=False)
            losing_app.new_game()
            losing_app.perform_action("talk_npc")

            self.assertEqual(losing_app.quest_state().status, QuestStatus.IN_PROGRESS)
            self.assertIn("hunt", {item.key for item in losing_app.available_actions()})

            winning_app = self._build_app(tmp_dir, win=True)
            winning_app.quest_session = losing_app.quest_session
            winning_app.party_members = losing_app.party_members
            winning_app.last_event_id = losing_app.last_event_id
            winning_app.inventory_state = losing_app.inventory_state

            hunt_logs = winning_app.perform_action("hunt")
            self.assertIn("quest_status_changed:quest.ch01.missing_port_record:ready_to_complete", hunt_logs)
            self.assertEqual(winning_app.quest_state().status, QuestStatus.READY_TO_COMPLETE)
            self.assertTrue(any(log.startswith("exp_applied:") for log in hunt_logs))
            self.assertGreater(winning_app.inventory_state["gold"], 0)

            winning_app.perform_action("report")
            self.assertEqual(winning_app.quest_state().status, QuestStatus.COMPLETED)

    def test_save_and_load_keeps_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.perform_action("talk_npc")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            status_logs = resumed.perform_action("status")
            inventory_logs = resumed.perform_action("inventory")

            self.assertTrue(any("last_event_id:event.ch01.port_request" in line for line in status_logs))
            self.assertEqual(resumed.quest_state().status, QuestStatus.READY_TO_COMPLETE)
            self.assertTrue(any(line.startswith("gold:") for line in inventory_logs))

    def test_continue_detects_missing_or_broken_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            ok, message = app.continue_game()
            self.assertFalse(ok)
            self.assertIn("見つかりません", message)

            save_path = Path(tmp_dir) / "slot_01.json"
            save_path.write_text("{broken json", encoding="utf-8")

            ok, message = app.continue_game()
            self.assertFalse(ok)
            self.assertIn("破損", message)


if __name__ == "__main__":
    unittest.main()
