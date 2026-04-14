from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.gathering.application.service import GatheringService
from game.gathering.domain.entities import GatheringLootEntry, GatheringNodeDefinition
from game.gathering.infrastructure.master_data_repository import GatheringNodeMasterDataRepository
from game.quest.domain.entities import BattleResult


class GatheringSliceTests(unittest.TestCase):
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

    def test_load_gathering_nodes(self) -> None:
        repo = GatheringNodeMasterDataRepository(Path("data/master"))
        nodes = repo.load_nodes(
            valid_item_ids={
                "item.consumable.antidote_leaf",
                "item.material.iron_fragment",
                "item.material.memory_shard",
            },
            valid_location_ids={"location.town.astel", "location.field.tidal_flats"},
        )
        self.assertEqual(len(nodes), 3)
        self.assertIn("gather.herb.astel_square_flowerbed", nodes)
        self.assertIn("gather.ore.tidal_flats_rust_ore", nodes)

    def test_service_detects_invalid_node_and_location_mismatch(self) -> None:
        service = GatheringService(
            {
                "gather.test.herb": GatheringNodeDefinition(
                    node_id="gather.test.herb",
                    location_id="location.town.astel",
                    name="テスト採取",
                    node_type="herb",
                    description="",
                    loot_entries=(
                        GatheringLootEntry(
                            item_id="item.consumable.antidote_leaf",
                            quantity=1,
                            drop_type="guaranteed",
                        ),
                    ),
                )
            }
        )

        invalid = service.gather(
            node_id="gather.test.missing",
            current_location_id="location.town.astel",
            world_flags=set(),
            gathered_node_ids=set(),
        )
        self.assertFalse(invalid.success)
        self.assertEqual(invalid.code, "invalid_node")

        mismatch = service.gather(
            node_id="gather.test.herb",
            current_location_id="location.field.tidal_flats",
            world_flags=set(),
            gathered_node_ids=set(),
        )
        self.assertFalse(mismatch.success)
        self.assertEqual(mismatch.code, "location_mismatch")

    def test_playable_slice_gathering_inventory_crafting_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            initial_recipe_lines = app.crafting_recipe_lines()
            initial_memory_edge_line = next(
                line for line in initial_recipe_lines if line.startswith("craft_recipe:recipe.craft.memory_edge")
            )
            self.assertIn("can_craft=False", initial_memory_edge_line)

            town_nodes = app.gathering_node_lines()
            self.assertTrue(any("gather.herb.astel_square_flowerbed" in line for line in town_nodes))

            town_gather_logs = app.gather_node("gather.herb.astel_square_flowerbed")
            self.assertIn("gathered:gather.herb.astel_square_flowerbed", town_gather_logs)
            self.assertTrue(any(line.startswith("gathered_item:item.consumable.antidote_leaf") for line in town_gather_logs))
            self.assertEqual(app.inventory_state["items"]["item.consumable.antidote_leaf"], 2)

            re_gather_logs = app.gather_node("gather.herb.astel_square_flowerbed")
            self.assertEqual(re_gather_logs, ["gather_failed:already_gathered:gather.herb.astel_square_flowerbed"])

            app.travel_to("location.field.tidal_flats")
            wrong_location = app.gather_node("gather.herb.astel_square_flowerbed")
            self.assertTrue(any("location_mismatch" in line for line in wrong_location))

            ore_logs = app.gather_node("gather.ore.tidal_flats_rust_ore")
            shard_logs = app.gather_node("gather.salvage.tidal_flats_memory_debris")
            self.assertIn("gathered:gather.ore.tidal_flats_rust_ore", ore_logs)
            self.assertIn("gathered:gather.salvage.tidal_flats_memory_debris", shard_logs)

            recipe_lines = app.crafting_recipe_lines()
            memory_edge_line = next(line for line in recipe_lines if line.startswith("craft_recipe:recipe.craft.memory_edge"))
            self.assertIn("can_craft=True", memory_edge_line)

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            self.assertIn("gather.herb.astel_square_flowerbed", resumed.gathered_node_ids)
            self.assertIn("gather.ore.tidal_flats_rust_ore", resumed.gathered_node_ids)
            self.assertEqual(
                resumed.gather_node("gather.ore.tidal_flats_rust_ore"),
                ["gather_failed:already_gathered:gather.ore.tidal_flats_rust_ore"],
            )


if __name__ == "__main__":
    unittest.main()
