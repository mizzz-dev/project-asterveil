from __future__ import annotations

from game.crafting.domain.entities import (
    CraftingRecipeDefinition,
    CraftingResult,
    MaterialRequirementStatus,
    RecipeResolution,
)


class CraftingService:
    def resolve(self, *, recipe: CraftingRecipeDefinition, inventory_items: dict[str, int]) -> RecipeResolution:
        requirements = tuple(
            MaterialRequirementStatus(
                item_id=ingredient.item_id,
                required=ingredient.quantity,
                owned=max(0, int(inventory_items.get(ingredient.item_id, 0))),
            )
            for ingredient in recipe.ingredients
        )
        missing = tuple(status for status in requirements if status.owned < status.required)

        aggregated_outputs: dict[str, int] = {}
        for output in recipe.outputs:
            inventory_item_id = output.inventory_item_id
            if not inventory_item_id:
                continue
            aggregated_outputs[inventory_item_id] = aggregated_outputs.get(inventory_item_id, 0) + output.quantity

        return RecipeResolution(
            can_craft=not missing,
            missing_materials=missing,
            required_materials=requirements,
            aggregated_outputs=aggregated_outputs,
        )

    def craft(
        self,
        *,
        recipe: CraftingRecipeDefinition,
        inventory_state: dict,
        count: int = 1,
    ) -> CraftingResult:
        if count <= 0:
            return CraftingResult(False, "invalid_count", f"craft_failed:invalid_count:{count}")

        items = inventory_state.setdefault("items", {})
        scaled_recipe = CraftingRecipeDefinition(
            recipe_id=recipe.recipe_id,
            name=recipe.name,
            category=recipe.category,
            ingredients=tuple(
                type(ingredient)(item_id=ingredient.item_id, quantity=ingredient.quantity * count)
                for ingredient in recipe.ingredients
            ),
            outputs=tuple(
                type(output)(item_id=output.item_id, equipment_id=output.equipment_id, quantity=output.quantity * count)
                for output in recipe.outputs
            ),
            description=recipe.description,
            unlock_flags=recipe.unlock_flags,
        )
        resolution = self.resolve(recipe=scaled_recipe, inventory_items=items)
        if not resolution.can_craft:
            missing = resolution.missing_materials[0]
            return CraftingResult(
                False,
                "missing_material",
                f"missing_material:{scaled_recipe.recipe_id}:{missing.item_id}:required={missing.required}:owned={missing.owned}",
                consumed=resolution.required_materials,
            )

        for requirement in resolution.required_materials:
            remaining = int(items.get(requirement.item_id, 0)) - requirement.required
            if remaining > 0:
                items[requirement.item_id] = remaining
            else:
                items.pop(requirement.item_id, None)

        for output_item_id, amount in resolution.aggregated_outputs.items():
            items[output_item_id] = int(items.get(output_item_id, 0)) + amount

        return CraftingResult(
            True,
            "crafted",
            f"crafted:{scaled_recipe.recipe_id}",
            consumed=resolution.required_materials,
            crafted=resolution.aggregated_outputs,
        )
