from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.app.infrastructure.equipment_upgrade_repository import EquipmentUpgradeMasterDataRepository
from game.quest.domain.entities import BattleResult


class EquipmentUpgradeSliceTests(unittest.TestCase):
    def _build_app(self, tmp_dir: str, recorder: dict | None = None) -> PlayableSliceApplication:
        def battle_executor(encounter_id: str, party_members=None) -> BattleResult:
            if recorder is not None and party_members:
                recorder["defense"] = party_members[0].defense
                recorder["max_hp"] = party_members[0].max_hp
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

    def test_load_equipment_upgrade_definitions(self) -> None:
        app = self._build_app(tempfile.mkdtemp())
        repo = EquipmentUpgradeMasterDataRepository(Path("data/master"))
        definitions = repo.load(
            valid_equipment_ids=set(app._equipment_definitions),
            valid_item_ids=set(app._item_definitions),
        )
        self.assertIn("equip.armor.tidebreaker_harness", definitions)
        self.assertEqual(len(definitions["equip.armor.tidebreaker_harness"].upgrade_levels), 2)
        self.assertEqual(definitions["equip.armor.tidebreaker_harness"].upgrade_levels[1].required_workshop_level, 3)

    def test_upgrade_requires_workshop_level(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.inventory_state["items"]["item.material.relic.deepsea_thread"] = 1
            app.inventory_state["items"]["item.material.iron_fragment"] = 2

            logs = app.upgrade_equipment("equip.armor.tidebreaker_harness")
            self.assertEqual(logs, ["equipment_upgrade_failed:insufficient_workshop_level"])

    def test_upgrade_requires_materials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.workshop_progress_state.level = 2
            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.inventory_state["items"]["item.material.iron_fragment"] = 2

            logs = app.upgrade_equipment("equip.armor.tidebreaker_harness")
            self.assertEqual(logs, ["equipment_upgrade_failed:insufficient_materials"])

    def test_upgrade_consumes_materials_and_updates_stats_and_battle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            recorder: dict[str, int] = {}
            app = self._build_app(tmp_dir, recorder)
            app.new_game()
            app.workshop_progress_state.level = 3
            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.inventory_state["items"]["item.material.relic.deepsea_thread"] = 2
            app.inventory_state["items"]["item.material.iron_fragment"] = 2
            app.inventory_state["items"]["item.material.miniboss.guardian_core"] = 1

            first_upgrade = app.upgrade_equipment("equip.armor.tidebreaker_harness")
            second_upgrade = app.upgrade_equipment("equip.armor.tidebreaker_harness")
            self.assertIn("equipment_upgrade_success:equip.armor.tidebreaker_harness:upgrade_level:+1:current=1", first_upgrade)
            self.assertIn("equipment_upgrade_success:equip.armor.tidebreaker_harness:upgrade_level:+1:current=2", second_upgrade)
            self.assertEqual(app.equipment_upgrade_levels["equip.armor.tidebreaker_harness"], 2)
            self.assertEqual(app.inventory_state["items"].get("item.material.relic.deepsea_thread", 0), 0)
            self.assertEqual(app.inventory_state["items"].get("item.material.iron_fragment", 0), 0)
            self.assertEqual(app.inventory_state["items"].get("item.material.miniboss.guardian_core", 0), 0)

            app.equip_item("char.main.rion", "armor", "equip.armor.tidebreaker_harness")
            member_line = next(line for line in app.party_member_lines() if line.startswith("member:char.main.rion"))
            self.assertIn("def=26", member_line)
            self.assertIn("equipment_upgrade_levels={'weapon': 0, 'armor': 2}", member_line)

            app._run_event_battle("encounter.ch01.port_wraith")
            self.assertEqual(recorder["defense"], 26)
            self.assertEqual(recorder["max_hp"], 160)

    def test_upgrade_persists_after_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.workshop_progress_state.level = 2
            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.inventory_state["items"]["item.material.relic.deepsea_thread"] = 1
            app.inventory_state["items"]["item.material.iron_fragment"] = 2

            app.upgrade_equipment("equip.armor.tidebreaker_harness")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            self.assertEqual(resumed.equipment_upgrade_levels.get("equip.armor.tidebreaker_harness"), 1)
            lines = resumed.workshop_equipment_upgrade_lines()
            self.assertTrue(any("current_level=1" in line for line in lines if line.startswith("equipment_upgrade_status:")))


if __name__ == "__main__":
    unittest.main()
