from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.app.infrastructure.equipment_salvage_repository import EquipmentSalvageMasterDataRepository
from game.quest.domain.entities import BattleResult


class EquipmentSalvageSliceTests(unittest.TestCase):
    def _build_app(self, tmp_dir: str) -> PlayableSliceApplication:
        def battle_executor(encounter_id: str) -> BattleResult:
            return BattleResult(encounter_id=encounter_id, player_won=True, defeated_enemy_ids=tuple())

        return PlayableSliceApplication(
            master_root=Path("data/master"),
            save_file_path=Path(tmp_dir) / "slot_01.json",
            battle_executor=battle_executor,
        )

    def test_load_equipment_salvage_definitions(self) -> None:
        app = self._build_app(tempfile.mkdtemp())
        repo = EquipmentSalvageMasterDataRepository(Path("data/master"))
        definitions = repo.load(
            valid_equipment_ids=set(app._equipment_definitions),
            valid_item_ids=set(app._item_definitions),
        )
        self.assertIn("equip.weapon.bronze_blade", definitions)
        self.assertEqual(definitions["equip.weapon.bronze_blade"].required_workshop_level, 1)
        self.assertIn("equip.armor.tidebreaker_harness", definitions)

    def test_salvage_failure_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            equipped_fail = app.salvage_equipment("equip.weapon.bronze_blade")
            self.assertEqual(equipped_fail, ["equipment_salvage_failed:equipped:equip.weapon.bronze_blade"])

            not_owned = app.salvage_equipment("equip.armor.tidebreaker_harness")
            self.assertEqual(not_owned, ["equipment_salvage_failed:not_owned:equip.armor.tidebreaker_harness"])

            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.workshop_progress_state.level = 2
            rank_fail = app.salvage_equipment("equip.armor.tidebreaker_harness")
            self.assertEqual(rank_fail, ["equipment_salvage_failed:insufficient_workshop_level"])

    def test_salvage_success_returns_materials_and_removes_equipment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["items"]["equip.weapon.bronze_blade"] = 2

            logs = app.salvage_equipment("equip.weapon.bronze_blade")
            self.assertIn("equipment_salvage_success:equip.weapon.bronze_blade", logs)
            self.assertIn("equipment_salvage_return:item.material.iron_fragment:x1", logs)
            self.assertEqual(app.inventory_state["items"].get("equip.weapon.bronze_blade"), 1)
            self.assertEqual(app.inventory_state["items"].get("item.material.iron_fragment"), 1)

    def test_salvage_upgrade_policy_and_upgrade_state_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.workshop_progress_state.level = 3
            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.equipment_upgrade_levels["equip.armor.tidebreaker_harness"] = 2

            logs = app.salvage_equipment("equip.armor.tidebreaker_harness")
            self.assertIn("equipment_salvage_success:equip.armor.tidebreaker_harness", logs)
            self.assertEqual(app.inventory_state["items"].get("equip.armor.tidebreaker_harness", 0), 0)
            self.assertEqual(app.inventory_state["items"].get("item.material.relic.deepsea_thread", 0), 1)
            self.assertEqual(app.inventory_state["items"].get("item.material.iron_fragment", 0), 2)
            self.assertNotIn("equip.armor.tidebreaker_harness", app.equipment_upgrade_levels)

    def test_salvaged_materials_can_be_reused_for_craft_and_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.workshop_progress_state.level = 2
            app.inventory_state["items"]["equip.weapon.bronze_blade"] = 3
            app.inventory_state["items"]["item.material.memory_shard"] = 2
            app.inventory_state["items"]["item.material.iron_fragment"] = 1
            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.inventory_state["items"]["item.material.relic.deepsea_thread"] = 1
            app.unlocked_recipe_ids.add("recipe.craft.memory_edge")
            app.discovered_recipe_ids.add("recipe.craft.memory_edge")

            app.salvage_equipment("equip.weapon.bronze_blade")
            app.salvage_equipment("equip.weapon.bronze_blade")
            craft_logs = app.craft_recipe("recipe.craft.memory_edge")
            self.assertIn("crafted:recipe.craft.memory_edge", craft_logs)

            upgrade_logs = app.upgrade_equipment("equip.armor.tidebreaker_harness")
            self.assertIn("equipment_upgrade_success:equip.armor.tidebreaker_harness:upgrade_level:+1:current=1", upgrade_logs)

    def test_salvage_persists_after_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["items"]["equip.weapon.bronze_blade"] = 2
            app.salvage_equipment("equip.weapon.bronze_blade")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            self.assertEqual(resumed.inventory_state["items"].get("equip.weapon.bronze_blade"), 1)
            self.assertEqual(resumed.inventory_state["items"].get("item.material.iron_fragment"), 1)


if __name__ == "__main__":
    unittest.main()
