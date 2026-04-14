from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.crafting.domain.entities import CraftingIngredient, CraftingOutput, CraftingRecipeDefinition
from game.crafting.domain.services import CraftingService
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
                "equip.weapon.memory_edge",
            },
            valid_equipment_ids={"equip.weapon.memory_edge"},
        )
        self.assertIn("recipe.craft.memory_tonic", recipes)
        self.assertIn("recipe.craft.memory_edge", recipes)

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
            app.buy_item("item.material.iron_fragment")

            recipe_lines = app.crafting_recipe_lines()
            self.assertTrue(any(line.startswith("craft_recipe:recipe.craft.memory_tonic") for line in recipe_lines))
            self.assertTrue(any(line.startswith("craft_recipe:recipe.craft.memory_edge") for line in recipe_lines))

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


if __name__ == "__main__":
    unittest.main()
