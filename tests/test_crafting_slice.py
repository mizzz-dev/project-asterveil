from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.crafting.domain.entities import CraftingIngredient, CraftingOutput, CraftingRecipeDefinition
from game.crafting.domain.services import CraftingService, RecipeDiscoveryService, RecipeUnlockService
from game.crafting.infrastructure.master_data_repository import CraftingMasterDataRepository
from game.quest.domain.entities import BattleResult


class CraftingSliceTests(unittest.TestCase):
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

    def test_load_crafting_recipes(self) -> None:
        repo = CraftingMasterDataRepository(Path("data/master"))
        recipes = repo.load_recipes(
            valid_item_ids={
                "item.material.memory_shard",
                "item.material.iron_fragment",
                "item.consumable.antidote_leaf",
                "item.consumable.memory_tonic",
                "item.consumable.focus_drop",
                "equip.weapon.memory_edge",
            },
            valid_equipment_ids={"equip.weapon.memory_edge", "equip.armor.vanguard_emblem"},
        )
        self.assertIn("recipe.craft.memory_tonic", recipes)
        self.assertIn("recipe.craft.memory_edge", recipes)
        self.assertIn("recipe.craft.herbal_focus_drop", recipes)
        self.assertEqual(recipes["recipe.craft.memory_edge"].unlock_conditions.required_completed_quest_ids, ("quest.ch01.missing_port_record",))
        self.assertEqual(recipes["recipe.craft.herbal_focus_drop"].unlock_conditions.required_flags, ("flag.helped_npc",))
        self.assertIn("recipe.craft.tidal_tonic", recipes)

    def test_load_recipe_discoveries(self) -> None:
        repo = CraftingMasterDataRepository(Path("data/master"))
        discoveries = repo.load_recipe_discoveries()
        self.assertTrue(any(d.unlock_source_type == "quest_complete" and d.source_id == "quest.ch01.missing_port_record" for d in discoveries))
        self.assertTrue(any(d.unlock_source_type == "dialogue_event" and d.source_id == "dialogue.workshop.recipe_lesson" for d in discoveries))
        self.assertTrue(any(d.unlock_source_type == "loot_item" and d.source_id == "item.key.recipe_book.tidal_tonic_notes" for d in discoveries))

    def test_recipe_discovery_service_handles_duplicate_book(self) -> None:
        repo = CraftingMasterDataRepository(Path("data/master"))
        service = RecipeDiscoveryService(
            repo.load_recipe_discoveries(),
            valid_recipe_ids={"recipe.craft.tidal_tonic", "recipe.craft.memory_edge", "recipe.craft.tidal_guard_talisman"},
        )
        discovered_recipe_ids: set[str] = set()
        discovered_book_ids: set[str] = set()
        unlocked_recipe_ids: set[str] = set()

        first = service.discover_from_items(
            gained_item_ids={"item.key.recipe_book.tidal_tonic_notes"},
            discovered_recipe_ids=discovered_recipe_ids,
            discovered_recipe_book_ids=discovered_book_ids,
            unlocked_recipe_ids=unlocked_recipe_ids,
        )
        self.assertTrue(any(log.startswith("recipe_book_discovered:") for log in first[0]))
        self.assertIn("recipe.craft.tidal_tonic", unlocked_recipe_ids)

        second = service.discover_from_items(
            gained_item_ids={"item.key.recipe_book.tidal_tonic_notes"},
            discovered_recipe_ids=discovered_recipe_ids,
            discovered_recipe_book_ids=discovered_book_ids,
            unlocked_recipe_ids=unlocked_recipe_ids,
        )
        self.assertTrue(any(log.startswith("recipe_book_already_known:") for log in second[1]))
        self.assertTrue(any(log.startswith("recipe_already_known:recipe.craft.tidal_tonic") for log in second[1]))

    def test_recipe_unlock_service_by_quest_and_flag(self) -> None:
        repo = CraftingMasterDataRepository(Path("data/master"))
        recipes = repo.load_recipes(
            valid_item_ids={
                "item.material.memory_shard",
                "item.material.iron_fragment",
                "item.consumable.antidote_leaf",
                "item.consumable.memory_tonic",
                "item.consumable.focus_drop",
            },
            valid_equipment_ids={"equip.weapon.memory_edge", "equip.armor.vanguard_emblem"},
        )
        unlock_service = RecipeUnlockService()
        unlocked_recipe_ids: set[str] = set()

        first = unlock_service.evaluate_and_apply_unlocks(
            recipes=recipes,
            unlocked_recipe_ids=unlocked_recipe_ids,
            world_flags=set(),
            completed_quest_ids=set(),
            current_location_id="location.town.astel",
        )
        self.assertEqual(first, ["recipe.craft.memory_tonic"])

        second = unlock_service.evaluate_and_apply_unlocks(
            recipes=recipes,
            unlocked_recipe_ids=unlocked_recipe_ids,
            world_flags=set(),
            completed_quest_ids={"quest.ch01.missing_port_record"},
            current_location_id="location.town.astel",
        )
        self.assertEqual(second, ["recipe.craft.memory_edge"])

        third = unlock_service.evaluate_and_apply_unlocks(
            recipes=recipes,
            unlocked_recipe_ids=unlocked_recipe_ids,
            world_flags={"flag.helped_npc"},
            completed_quest_ids={"quest.ch01.missing_port_record"},
            current_location_id="location.town.astel",
        )
        self.assertEqual(third, ["recipe.craft.herbal_focus_drop"])

        duplicate = unlock_service.evaluate_and_apply_unlocks(
            recipes=recipes,
            unlocked_recipe_ids=unlocked_recipe_ids,
            world_flags={"flag.helped_npc"},
            completed_quest_ids={"quest.ch01.missing_port_record"},
            current_location_id="location.town.astel",
        )
        self.assertEqual(duplicate, [])

    def test_crafting_service_success_and_missing(self) -> None:
        recipe = CraftingRecipeDefinition(
            recipe_id="recipe.test",
            name="test",
            category="consumable",
            ingredients=(
                CraftingIngredient(item_id="item.a", quantity=2),
                CraftingIngredient(item_id="item.b", quantity=1),
            ),
            outputs=(
                CraftingOutput(item_id="item.out", quantity=1),
                CraftingOutput(item_id="item.out", quantity=2),
            ),
        )
        service = CraftingService()

        missing = service.craft(recipe=recipe, inventory_state={"items": {"item.a": 1, "item.b": 1}})
        self.assertFalse(missing.success)
        self.assertEqual(missing.code, "missing_material")

        inventory = {"items": {"item.a": 3, "item.b": 1}}
        success = service.craft(recipe=recipe, inventory_state=inventory)
        self.assertTrue(success.success)
        self.assertEqual(inventory["items"]["item.a"], 1)
        self.assertNotIn("item.b", inventory["items"])
        self.assertEqual(inventory["items"]["item.out"], 3)

    def test_playable_slice_crafting_item_equipment_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["items"]["item.material.memory_shard"] = 3
            app.inventory_state["items"]["item.material.iron_fragment"] = 1
            app.buy_item("item.material.iron_fragment")
            dialogue_logs = app.talk_to_npc("npc.astel.elder", choice_selector=lambda _, __: "choice.help")
            self.assertIn("recipe_unlocked:recipe.craft.herbal_focus_drop:長老の助言で集中雫の応用調合を習得した。", dialogue_logs)

            recipe_lines = app.crafting_recipe_lines()
            self.assertTrue(any("craft_recipe:recipe.craft.memory_tonic" in line and "unlock=解放済み" in line for line in recipe_lines))
            self.assertTrue(any("craft_recipe:recipe.craft.memory_edge" in line and "unlock=未解放" in line for line in recipe_lines))
            self.assertEqual(app.craft_recipe("recipe.craft.memory_edge"), ["craft_failed:recipe_locked:recipe.craft.memory_edge"])

            app.accept_quest("quest.ch01.missing_port_record")
            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            report_logs = app.perform_action("report")
            self.assertIn("recipe_discovered:recipe.craft.memory_edge:港の依頼達成報酬で鍛造図面を受け取った。", report_logs)

            app.accept_quest("quest.ch01.memory_fragment_delivery")
            app.inventory_state["items"]["item.material.memory_shard"] = 5
            app.travel_to("location.town.astel")
            app.turn_in_quest_items("quest.ch01.memory_fragment_delivery", auto_complete=True)
            workshop_logs = app.talk_to_npc(
                "npc.astel.workshop_master",
                choice_selector=lambda choices, _step_id: choices[0][0],
            )
            self.assertTrue(
                any(line.startswith("recipe_discovered:recipe.craft.tidal_tonic:") for line in workshop_logs)
                or any(line.startswith("recipe_already_known:recipe.craft.tidal_tonic") for line in workshop_logs)
            )
            self.assertTrue(any("workshop_recipe:recipe.craft.tidal_tonic" in line and "discovery=発見済み" in line for line in workshop_logs))

            duplicate_book_logs = app._apply_recipe_discovery_for_items({"item.key.recipe_book.tidal_tonic_notes"})
            self.assertTrue(any(line.startswith("recipe_book_already_known:") for line in duplicate_book_logs))

            tonic_logs = app.craft_recipe("recipe.craft.memory_tonic")
            self.assertIn("crafted:recipe.craft.memory_tonic", tonic_logs)
            self.assertEqual(app.inventory_state["items"]["item.consumable.memory_tonic"], 1)

            app.party_members[0].current_hp = 20
            use_logs = app.use_item("item.consumable.memory_tonic", "char.main.rion")
            self.assertEqual(use_logs, ["item_used:item.consumable.memory_tonic:target=char.main.rion"])
            self.assertEqual(app.party_members[0].current_hp, 110)

            edge_logs = app.craft_recipe("recipe.craft.memory_edge")
            self.assertIn("crafted:recipe.craft.memory_edge", edge_logs)
            equip_logs = app.equip_item("char.main.rion", "weapon", "equip.weapon.memory_edge")
            self.assertIn("equip_succeeded:char.main.rion:weapon:equip.weapon.memory_edge", equip_logs)

            missing_logs = app.craft_recipe("recipe.craft.memory_edge")
            self.assertTrue(any(line.startswith("missing_material:recipe.craft.memory_edge") for line in missing_logs))

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            self.assertEqual(resumed.inventory_state["items"].get("item.consumable.memory_tonic", 0), 0)
            self.assertEqual(resumed.party_members[0].equipped["weapon"], "equip.weapon.memory_edge")
            self.assertIn("recipe.craft.herbal_focus_drop", resumed.unlocked_recipe_ids)
            self.assertIn("recipe.craft.tidal_tonic", resumed.discovered_recipe_ids)


if __name__ == "__main__":
    unittest.main()
