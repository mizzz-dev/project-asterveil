from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.app.infrastructure.workshop_order_repository import WorkshopOrderMasterDataRepository
from game.quest.domain.entities import BattleResult


class WorkshopOrderSliceTests(unittest.TestCase):
    def _build_app(self, tmp_dir: str) -> PlayableSliceApplication:
        def battle_executor(encounter_id: str) -> BattleResult:
            return BattleResult(
                encounter_id=encounter_id,
                player_won=True,
                defeated_enemy_ids=("enemy.ch01.port_wraith",),
            )

        return PlayableSliceApplication(
            master_root=Path("data/master"),
            save_file_path=Path(tmp_dir) / "slot_01.json",
            battle_executor=battle_executor,
        )

    def test_workshop_order_master_data_loading(self) -> None:
        repo = WorkshopOrderMasterDataRepository(Path("data/master"))
        orders, ranks = repo.load()
        self.assertIn("quest.ch01.workshop_iron_delivery", orders)
        self.assertIn("quest.ch01.workshop_tonic_order", orders)
        self.assertTrue(orders["quest.ch01.workshop_iron_delivery"].repeatable)
        self.assertTrue(orders["quest.ch01.workshop_tonic_order"].require_crafted_item)
        self.assertEqual(ranks[0].level, 1)
        self.assertEqual(ranks[1].level, 2)

    def test_repeatable_workshop_order_progress_rank_up_and_recipe_unlock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            app.inventory_state.setdefault("items", {})["item.material.iron_fragment"] = 6
            self.assertEqual(
                app.craft_recipe("recipe.craft.workshop_guard_oil"),
                ["craft_failed:recipe_locked:recipe.craft.workshop_guard_oil"],
            )

            before_rank = app.talk_to_npc("npc.astel.workshop_master")
            self.assertTrue(any("workshop_progress:rank=1" in line for line in before_rank))

            app.accept_quest("quest.ch01.workshop_iron_delivery")
            turn_in_logs = app.turn_in_quest_items("quest.ch01.workshop_iron_delivery")
            self.assertTrue(any(line.startswith("turn_in_success:quest.ch01.workshop_iron_delivery") for line in turn_in_logs))
            complete_logs = app.report_ready_quest()
            self.assertTrue(any(line == "workshop_progress:0->30" for line in complete_logs))
            self.assertEqual(app.workshop_progress_state.level, 1)

            app.travel_to("location.field.tidal_flats")
            app.travel_to("location.town.astel")
            self.assertEqual(
                app.accept_quest("quest.ch01.workshop_iron_delivery"),
                ["quest_reaccepted:quest.ch01.workshop_iron_delivery"],
            )

            turn_in_logs_2 = app.turn_in_quest_items("quest.ch01.workshop_iron_delivery")
            self.assertTrue(any(line.startswith("turn_in_success:quest.ch01.workshop_iron_delivery") for line in turn_in_logs_2))
            complete_logs_2 = app.report_ready_quest()
            self.assertTrue(any(line == "workshop_rank_up:1->2" for line in complete_logs_2))
            self.assertTrue(
                any(line == "recipe_unlocked_by_workshop_rank:2:recipe.craft.workshop_guard_oil" for line in complete_logs_2)
            )
            self.assertEqual(app.workshop_progress_state.level, 2)

            crafted = app.craft_recipe("recipe.craft.workshop_guard_oil")
            self.assertIn("crafted:recipe.craft.workshop_guard_oil", crafted)

            after_rank = app.talk_to_npc("npc.astel.workshop_master")
            self.assertTrue(any("workshop_progress:rank=2" in line for line in after_rank))

    def test_crafted_item_order_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.workshop_progress_state.level = 2
            app.quest_session.world_flags.add("flag.workshop.rank.2")
            app.workshop_progress_state.unlocked_recipe_ids.add("recipe.craft.workshop_guard_oil")

            app.inventory_state.setdefault("items", {})["item.material.memory_shard"] = 2
            app.inventory_state["items"]["item.consumable.antidote_leaf"] = 3
            craft_logs = app.craft_recipe("recipe.craft.memory_tonic")
            self.assertIn("crafted:recipe.craft.memory_tonic", craft_logs)

            accepted = app.accept_quest("quest.ch01.workshop_tonic_order")
            self.assertEqual(accepted, ["quest_accepted:quest.ch01.workshop_tonic_order"])
            turn_in_logs = app.turn_in_quest_items("quest.ch01.workshop_tonic_order")
            self.assertTrue(any(line.startswith("turn_in_success:quest.ch01.workshop_tonic_order") for line in turn_in_logs))
            report_logs = app.report_ready_quest()
            self.assertTrue(any(line.startswith("workshop_order_completed:quest.ch01.workshop_tonic_order") for line in report_logs))

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            self.assertEqual(resumed.workshop_progress_state.level, app.workshop_progress_state.level)
            self.assertEqual(resumed.workshop_progress_state.progress, app.workshop_progress_state.progress)
            self.assertEqual(
                resumed.workshop_order_completion_counts.get("quest.ch01.workshop_tonic_order"),
                app.workshop_order_completion_counts.get("quest.ch01.workshop_tonic_order"),
            )


if __name__ == "__main__":
    unittest.main()
