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
            self.assertEqual(app.inventory_state["items"]["item.consumable.mini_potion"], 3)

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
            app.party_members[0].current_hp = 50
            app.use_item("item.consumable.mini_potion", "char.main.rion")
            app.perform_action("talk_npc")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            status_logs = resumed.perform_action("status")
            inventory_logs = resumed.perform_action("inventory")

            self.assertTrue(any("last_event_id:event.ch01.port_request" in line for line in status_logs))
            self.assertEqual(resumed.quest_state().status, QuestStatus.READY_TO_COMPLETE)
            self.assertTrue(any(line.startswith("gold:") for line in inventory_logs))
            self.assertEqual(resumed.party_members[0].current_hp, 90)
            self.assertEqual(resumed.inventory_state["items"]["item.consumable.mini_potion"], 2)

    def test_use_item_updates_hp_sp_and_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.party_members[0].current_hp = 60
            app.party_members[0].current_sp = 30

            hp_logs = app.use_item("item.consumable.mini_potion", "char.main.rion")
            sp_logs = app.use_item("item.consumable.focus_drop", "char.main.rion")

            self.assertIn("item_used:item.consumable.mini_potion:target=char.main.rion", hp_logs)
            self.assertIn("item_used:item.consumable.focus_drop:target=char.main.rion", sp_logs)
            self.assertEqual(app.party_members[0].current_hp, 100)
            self.assertEqual(app.party_members[0].current_sp, 55)
            self.assertEqual(app.inventory_state["items"]["item.consumable.mini_potion"], 2)
            self.assertEqual(app.inventory_state["items"]["item.consumable.focus_drop"], 1)

    def test_use_item_failure_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            no_stock = app.use_item("item.consumable.unknown", "char.main.rion")
            self.assertEqual(no_stock, ["item_use_failed:no_stock:item.consumable.unknown"])

            invalid_target = app.use_item("item.consumable.mini_potion", "char.main.unknown")
            self.assertEqual(invalid_target, ["item_use_failed:invalid_target:char.main.unknown"])

            app.inventory_state["items"]["item.consumable.focus_drop"] = 0
            out_of_stock = app.use_item("item.consumable.focus_drop", "char.main.rion")
            self.assertEqual(out_of_stock, ["item_use_failed:no_stock:item.consumable.focus_drop"])

    def test_status_and_usable_item_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            logs = app.perform_action("status")
            usable = app.perform_action("use_item")
            self.assertTrue(any(line.startswith("member:char.main.rion") for line in logs))
            self.assertTrue(any(line.startswith("usable_item:item.consumable.mini_potion") for line in usable))

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
