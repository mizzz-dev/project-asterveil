from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.location.domain.treasure_services import TreasureService
from game.location.infrastructure.master_data_repository import LocationMasterDataRepository
from game.location.infrastructure.treasure_repository import TreasureMasterDataRepository
from game.quest.domain.entities import BattleResult


class LocationTreasureSliceTests(unittest.TestCase):
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

    def test_repository_loads_location_reward_nodes(self) -> None:
        location_repo = LocationMasterDataRepository(Path("data/master"))
        locations = location_repo.load_locations()
        repo = TreasureMasterDataRepository(Path("data/master"))
        nodes = repo.load_nodes(
            valid_item_ids={
                "item.consumable.focus_drop",
                "item.material.iron_fragment",
                "item.consumable.mini_potion",
                "item.consumable.antidote_leaf",
                "item.key.recipe_book.tidal_tonic_notes",
                "item.material.memory_shard",
            },
            valid_equipment_ids={"equip.weapon.iron_blade"},
            valid_location_ids=set(locations),
        )
        self.assertGreaterEqual(len(nodes), 3)
        self.assertIn("reward.treasure.astel_storehouse_chest", nodes)
        self.assertIn("reward.treasure.tidal_flats_drift_chest", nodes)
        self.assertIn("reward.discovery.sunken_recipe_notes", nodes)
        self.assertEqual(nodes["reward.discovery.sunken_recipe_notes"].node_type, "discoverable_cache")

    def test_treasure_service_resolve_and_apply_separated(self) -> None:
        location_repo = LocationMasterDataRepository(Path("data/master"))
        locations = location_repo.load_locations()
        repo = TreasureMasterDataRepository(Path("data/master"))
        nodes = repo.load_nodes(
            valid_item_ids={
                "item.consumable.focus_drop",
                "item.material.iron_fragment",
                "item.consumable.mini_potion",
                "item.consumable.antidote_leaf",
                "item.key.recipe_book.tidal_tonic_notes",
                "item.material.memory_shard",
            },
            valid_equipment_ids={"equip.weapon.iron_blade"},
            valid_location_ids=set(locations),
        )
        service = TreasureService()
        opened_state: set[str] = set()
        node = nodes["reward.treasure.astel_storehouse_chest"]
        result = service.open_node(
            node=node,
            current_location_id="location.town.astel",
            world_flags=set(),
            opened_node_ids=opened_state,
            facility_levels={},
        )
        self.assertTrue(result.success)
        self.assertIn("item.consumable.focus_drop", result.gained_items)

        inventory = {"gold": 0, "items": {}}
        service.apply_to_inventory(inventory_state=inventory, gained_items=result.gained_items)
        self.assertEqual(inventory["items"]["item.consumable.focus_drop"], 1)

    def test_playable_treasure_open_inventory_recipe_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            town_lines = app.treasure_node_lines()
            self.assertTrue(any(line.startswith("treasure_node:reward.treasure.astel_storehouse_chest") for line in town_lines))

            town_open_logs = app.open_treasure_node("reward.treasure.astel_storehouse_chest")
            self.assertIn("treasure_opened:reward.treasure.astel_storehouse_chest", town_open_logs)
            self.assertGreaterEqual(app.inventory_state["items"].get("item.material.iron_fragment", 0), 1)
            self.assertEqual(
                app.open_treasure_node("reward.treasure.astel_storehouse_chest"),
                ["treasure_already_opened:reward.treasure.astel_storehouse_chest"],
            )

            app.accept_quest("quest.ch01.missing_port_record")
            app.travel_to("location.field.tidal_flats")
            field_open_logs = app.open_treasure_node("reward.treasure.tidal_flats_drift_chest")
            self.assertIn("treasure_opened:reward.treasure.tidal_flats_drift_chest", field_open_logs)
            self.assertGreaterEqual(app.inventory_state["items"].get("equip.weapon.iron_blade", 0), 1)

            app.travel_to("location.town.astel")
            app._complete_quest("quest.ch01.missing_port_record")
            app.travel_to("location.dungeon.sunken_storehouse")
            locked_none = app.open_treasure_node("reward.discovery.sunken_recipe_notes")
            self.assertIn("treasure_opened:reward.discovery.sunken_recipe_notes", locked_none)
            self.assertIn("item.key.recipe_book.tidal_tonic_notes", app.inventory_state["items"])
            self.assertTrue(any(log.startswith("recipe_discovered_from_treasure:") for log in locked_none))

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            self.assertIn("reward.treasure.astel_storehouse_chest", resumed.opened_treasure_node_ids)
            self.assertIn("reward.treasure.tidal_flats_drift_chest", resumed.opened_treasure_node_ids)
            self.assertIn("reward.discovery.sunken_recipe_notes", resumed.opened_treasure_node_ids)

    def test_treasure_open_fails_when_condition_unmet_or_location_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            mismatch = app.open_treasure_node("reward.treasure.tidal_flats_drift_chest")
            self.assertEqual(mismatch, ["treasure_open_failed:location_mismatch:reward.treasure.tidal_flats_drift_chest"])

            locked = app.open_treasure_node("reward.discovery.astel_locked_cache")
            self.assertEqual(locked, ["treasure_open_failed:required_flag_missing:reward.discovery.astel_locked_cache"])


if __name__ == "__main__":
    unittest.main()
