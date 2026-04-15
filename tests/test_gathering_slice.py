from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.gathering.domain.services import GatheringRespawnService, GatheringService
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

    def test_repository_loads_gathering_nodes(self) -> None:
        repo = GatheringNodeMasterDataRepository(Path("data/master"))
        nodes = repo.load_nodes(
            valid_item_ids={
                "item.consumable.antidote_leaf",
                "item.material.memory_shard",
                "item.material.iron_fragment",
            },
            valid_location_ids={
                "location.town.astel",
                "location.field.tidal_flats",
                "location.dungeon.sunken_storehouse",
                "location.dungeon.tidegate_ruins",
            },
        )
        self.assertGreaterEqual(len(nodes), 3)
        self.assertIn("node.herb.astel_backyard_01", nodes)
        self.assertIn("node.ore.tidal_flats_01", nodes)
        self.assertEqual(nodes["node.herb.astel_backyard_01"].respawn_rule, "on_rest")
        self.assertEqual(nodes["node.ore.tidal_flats_01"].respawn_rule, "on_return_to_hub")
        self.assertEqual(nodes["node.salvage.sunken_storehouse_01"].respawn_rule, "none")

    def test_location_dependent_listing_and_gathering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            town_nodes = app.gathering_node_lines()
            self.assertTrue(any(line.startswith("gather_node:node.herb.astel_backyard_01") for line in town_nodes))

            wrong_location = app.gather_from_node("node.ore.tidal_flats_01")
            self.assertEqual(wrong_location, ["gather_failed:location_mismatch:node.ore.tidal_flats_01"])

            gather_logs = app.gather_from_node("node.herb.astel_backyard_01")
            self.assertTrue(gather_logs[0].startswith("gathered:node.herb.astel_backyard_01"))
            self.assertIn("item.consumable.antidote_leaf", app.inventory_state["items"])

            gathered_again = app.gather_from_node("node.herb.astel_backyard_01")
            self.assertEqual(gathered_again, ["gather_failed:already_gathered:node.herb.astel_backyard_01"])

            missing = app.gather_from_node("node.unknown")
            self.assertEqual(missing, ["gather_failed:node_not_found:node.unknown"])

    def test_gathering_materials_are_usable_for_crafting_and_persist_on_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            app.gather_from_node("node.herb.astel_backyard_01")
            app.quest_session.world_flags.add("flag.ch01.port_record_restored")
            app._travel_service.evaluate_unlocks(app.location_state, app.quest_session.world_flags)
            app.travel_to("location.dungeon.sunken_storehouse")
            app.gather_from_node("node.salvage.sunken_storehouse_01")

            craft_logs = app.craft_recipe("recipe.craft.memory_tonic")
            self.assertIn("crafted:recipe.craft.memory_tonic", craft_logs)

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            self.assertIn("node.herb.astel_backyard_01", resumed.gathered_node_ids)
            self.assertIn("node.salvage.sunken_storehouse_01", resumed.gathered_node_ids)
            self.assertGreaterEqual(resumed.inventory_state["items"].get("item.consumable.memory_tonic", 0), 1)

    def test_on_rest_and_on_return_to_hub_respawn_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["gold"] = 500

            app.gather_from_node("node.herb.astel_backyard_01")
            self.assertEqual(
                app.gather_from_node("node.herb.astel_backyard_01"),
                ["gather_failed:already_gathered:node.herb.astel_backyard_01"],
            )

            stay_logs = app.stay_at_inn()
            self.assertIn("gathering_respawned:on_rest:count=1", stay_logs)
            self.assertIn(
                "gathering_respawned_node:on_rest:node.herb.astel_backyard_01",
                stay_logs,
            )
            self.assertTrue(
                app.gather_from_node("node.herb.astel_backyard_01")[0].startswith(
                    "gathered:node.herb.astel_backyard_01"
                )
            )

            app.accept_quest("quest.ch01.missing_port_record")
            app.travel_to("location.field.tidal_flats")
            app.gather_from_node("node.ore.tidal_flats_01")
            self.assertEqual(
                app.gather_from_node("node.ore.tidal_flats_01"),
                ["gather_failed:already_gathered:node.ore.tidal_flats_01"],
            )
            return_logs = app.travel_to("location.town.astel")
            self.assertIn("travel_succeeded:location.town.astel", return_logs)
            self.assertIn("gathering_respawned:on_return_to_hub:count=1", return_logs)
            app.travel_to("location.field.tidal_flats")
            self.assertTrue(
                app.gather_from_node("node.ore.tidal_flats_01")[0].startswith(
                    "gathered:node.ore.tidal_flats_01"
                )
            )

    def test_respawn_rule_none_is_not_respawned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["gold"] = 500
            app.quest_session.world_flags.add("flag.ch01.port_record_restored")
            app._travel_service.evaluate_unlocks(app.location_state, app.quest_session.world_flags)

            app.travel_to("location.dungeon.sunken_storehouse")
            app.gather_from_node("node.salvage.sunken_storehouse_01")
            app.travel_to("location.town.astel")
            stay_logs = app.stay_at_inn()
            self.assertIn("gathering_respawned:on_rest:count=0", stay_logs)
            return_logs = app.travel_to("location.dungeon.sunken_storehouse")
            self.assertIn("travel_succeeded:location.dungeon.sunken_storehouse", return_logs)

            not_respawned = app.gather_from_node("node.salvage.sunken_storehouse_01")
            self.assertEqual(
                not_respawned,
                ["gather_failed:already_gathered:node.salvage.sunken_storehouse_01"],
            )

    def test_gathering_state_keeps_respawned_nodes_after_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["gold"] = 500
            app.gather_from_node("node.herb.astel_backyard_01")
            app.stay_at_inn()
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            self.assertNotIn("node.herb.astel_backyard_01", resumed.gathered_node_ids)
            self.assertTrue(
                resumed.gather_from_node("node.herb.astel_backyard_01")[0].startswith(
                    "gathered:node.herb.astel_backyard_01"
                )
            )

    def test_respawn_service_detects_unknown_gathered_node_id(self) -> None:
        repo = GatheringNodeMasterDataRepository(Path("data/master"))
        nodes = repo.load_nodes(
            valid_item_ids={
                "item.consumable.antidote_leaf",
                "item.material.memory_shard",
                "item.material.iron_fragment",
            },
            valid_location_ids={
                "location.town.astel",
                "location.field.tidal_flats",
                "location.dungeon.sunken_storehouse",
                "location.dungeon.tidegate_ruins",
            },
        )
        service = GatheringRespawnService()
        with self.assertRaisesRegex(ValueError, "gathering node not found"):
            service.respawn_by_trigger(
                trigger="on_rest",
                nodes=nodes,
                gathered_node_ids={"node.unknown"},
            )

    def test_resolve_and_inventory_apply_are_separated(self) -> None:
        repo = GatheringNodeMasterDataRepository(Path("data/master"))
        nodes = repo.load_nodes(
            valid_item_ids={
                "item.consumable.antidote_leaf",
                "item.material.memory_shard",
                "item.material.iron_fragment",
            },
            valid_location_ids={
                "location.town.astel",
                "location.field.tidal_flats",
                "location.dungeon.sunken_storehouse",
                "location.dungeon.tidegate_ruins",
            },
        )
        service = GatheringService(roll_provider=lambda: 0.0)
        node = nodes["node.herb.astel_backyard_01"]
        gathered_state: set[str] = set()
        result = service.gather(
            node=node,
            current_location_id="location.town.astel",
            world_flags=set(),
            gathered_node_ids=gathered_state,
        )
        self.assertTrue(result.success)
        inventory_state = {"gold": 0, "items": {}}
        service.apply_to_inventory(inventory_state=inventory_state, gained_items=result.gained_items)
        self.assertGreaterEqual(inventory_state["items"].get("item.consumable.antidote_leaf", 0), 1)


if __name__ == "__main__":
    unittest.main()
