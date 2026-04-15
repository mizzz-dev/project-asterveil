from __future__ import annotations

import json
from pathlib import Path

from game.crafting.domain.entities import (
    CraftingIngredient,
    CraftingOutput,
    CraftingRecipeDefinition,
    RecipeUnlockConditions,
)


class CraftingMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_recipes(
        self,
        *,
        valid_item_ids: set[str],
        valid_equipment_ids: set[str],
    ) -> dict[str, CraftingRecipeDefinition]:
        raw = json.loads((self._root / "crafting_recipes.sample.json").read_text(encoding="utf-8"))
        recipes: dict[str, CraftingRecipeDefinition] = {}
        for entry in raw:
            recipe_id = str(entry.get("recipe_id") or "")
            if not recipe_id:
                raise ValueError("crafting_recipes.sample.json missing field=recipe_id")
            ingredients_raw = entry.get("ingredients") or []
            if not ingredients_raw:
                raise ValueError(f"crafting_recipes.sample.json ingredients required recipe_id={recipe_id}")
            outputs_raw = entry.get("outputs") or []
            if not outputs_raw:
                raise ValueError(f"crafting_recipes.sample.json outputs required recipe_id={recipe_id}")

            ingredients: list[CraftingIngredient] = []
            for ingredient in ingredients_raw:
                item_id = str(ingredient.get("item_id") or "")
                quantity = int(ingredient.get("quantity", 0))
                if not item_id:
                    raise ValueError(f"crafting_recipes.sample.json ingredient missing item_id recipe_id={recipe_id}")
                if item_id not in valid_item_ids:
                    raise ValueError(f"crafting_recipes.sample.json unknown ingredient item_id={item_id} recipe_id={recipe_id}")
                if quantity <= 0:
                    raise ValueError(f"crafting_recipes.sample.json ingredient quantity must be > 0 recipe_id={recipe_id}")
                ingredients.append(CraftingIngredient(item_id=item_id, quantity=quantity))

            outputs: list[CraftingOutput] = []
            for output in outputs_raw:
                quantity = int(output.get("quantity", 0))
                if quantity <= 0:
                    raise ValueError(f"crafting_recipes.sample.json output quantity must be > 0 recipe_id={recipe_id}")
                item_id = output.get("item_id")
                equipment_id = output.get("equipment_id")
                if bool(item_id) == bool(equipment_id):
                    raise ValueError(
                        f"crafting_recipes.sample.json output requires either item_id or equipment_id recipe_id={recipe_id}"
                    )
                if item_id and str(item_id) not in valid_item_ids:
                    raise ValueError(f"crafting_recipes.sample.json unknown output item_id={item_id} recipe_id={recipe_id}")
                if equipment_id and str(equipment_id) not in valid_equipment_ids:
                    raise ValueError(
                        f"crafting_recipes.sample.json unknown output equipment_id={equipment_id} recipe_id={recipe_id}"
                    )
                outputs.append(
                    CraftingOutput(
                        item_id=str(item_id) if item_id else None,
                        equipment_id=str(equipment_id) if equipment_id else None,
                        quantity=quantity,
                    )
                )

            recipes[recipe_id] = CraftingRecipeDefinition(
                recipe_id=recipe_id,
                name=str(entry.get("name") or recipe_id),
                category=str(entry.get("category") or "generic"),
                ingredients=tuple(ingredients),
                outputs=tuple(outputs),
                description=str(entry.get("description") or ""),
                unlock_flags=tuple(str(flag_id) for flag_id in entry.get("unlock_flags", [])),
                unlock_conditions=self._build_unlock_conditions(entry, recipe_id),
                visible_before_unlock=bool(entry.get("visible_before_unlock", True)),
                unlock_message=str(entry.get("unlock_message") or ""),
            )

        return recipes

    def _build_unlock_conditions(self, entry: dict, recipe_id: str) -> RecipeUnlockConditions:
        raw_conditions = entry.get("unlock_conditions")
        if raw_conditions is None:
            return RecipeUnlockConditions()
        if not isinstance(raw_conditions, dict):
            raise ValueError(f"crafting_recipes.sample.json unlock_conditions must be object recipe_id={recipe_id}")
        for field_name in ("required_flags", "required_completed_quest_ids", "required_location_ids"):
            value = raw_conditions.get(field_name, [])
            if not isinstance(value, list):
                raise ValueError(
                    f"crafting_recipes.sample.json unlock_conditions.{field_name} must be array recipe_id={recipe_id}"
                )
        return RecipeUnlockConditions(
            required_flags=tuple(str(flag_id) for flag_id in raw_conditions.get("required_flags", [])),
            required_completed_quest_ids=tuple(
                str(quest_id) for quest_id in raw_conditions.get("required_completed_quest_ids", [])
            ),
            required_location_ids=tuple(str(location_id) for location_id in raw_conditions.get("required_location_ids", [])),
        )
