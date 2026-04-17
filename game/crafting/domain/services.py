from __future__ import annotations

from game.crafting.domain.entities import (
    CraftingRecipeDefinition,
    CraftingResult,
    MaterialRequirementStatus,
    RecipeDiscoveryDefinition,
    RecipeAvailabilityStatus,
    RecipeUnlockConditions,
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
            recipe_tier=recipe.recipe_tier,
            required_workshop_level=recipe.required_workshop_level,
            required_recipe_discovery=recipe.required_recipe_discovery,
            unlock_flags=recipe.unlock_flags,
            unlock_conditions=recipe.unlock_conditions,
            visible_before_unlock=recipe.visible_before_unlock,
            unlock_message=recipe.unlock_message,
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


class RecipeUnlockService:
    def evaluate_and_apply_unlocks(
        self,
        *,
        recipes: dict[str, CraftingRecipeDefinition],
        unlocked_recipe_ids: set[str],
        world_flags: set[str],
        completed_quest_ids: set[str],
        current_location_id: str | None = None,
    ) -> list[str]:
        newly_unlocked: list[str] = []
        for recipe_id, recipe in sorted(recipes.items()):
            if recipe_id in unlocked_recipe_ids:
                continue
            if not self._is_unlockable(
                recipe=recipe,
                world_flags=world_flags,
                completed_quest_ids=completed_quest_ids,
                current_location_id=current_location_id,
            ):
                continue
            unlocked_recipe_ids.add(recipe_id)
            newly_unlocked.append(recipe_id)
        return newly_unlocked

    def build_availability(
        self,
        *,
        recipes: dict[str, CraftingRecipeDefinition],
        unlocked_recipe_ids: set[str],
        world_flags: set[str],
        completed_quest_ids: set[str],
        current_location_id: str | None,
        crafting_service: CraftingService,
        inventory_items: dict[str, int],
    ) -> list[RecipeAvailabilityStatus]:
        statuses: list[RecipeAvailabilityStatus] = []
        for recipe_id, recipe in sorted(recipes.items()):
            unlocked = recipe_id in unlocked_recipe_ids
            visible = unlocked or recipe.visible_before_unlock
            if not visible:
                continue
            if unlocked:
                resolution = crafting_service.resolve(recipe=recipe, inventory_items=inventory_items)
                statuses.append(
                    RecipeAvailabilityStatus(
                        recipe_id=recipe_id,
                        unlocked=True,
                        can_craft=resolution.can_craft,
                        visible=True,
                        lock_reason="",
                    )
                )
                continue
            lock_reason = self.lock_reason(
                recipe=recipe,
                world_flags=world_flags,
                completed_quest_ids=completed_quest_ids,
                current_location_id=current_location_id,
            )
            statuses.append(
                RecipeAvailabilityStatus(
                    recipe_id=recipe_id,
                    unlocked=False,
                    can_craft=False,
                    visible=True,
                    lock_reason=lock_reason,
                )
            )
        return statuses

    def lock_reason(
        self,
        *,
        recipe: CraftingRecipeDefinition,
        world_flags: set[str],
        completed_quest_ids: set[str],
        current_location_id: str | None,
    ) -> str:
        conditions = self._normalized_conditions(recipe)
        if any(flag_id not in world_flags for flag_id in conditions.required_flags):
            return "required_flag_missing"
        if any(quest_id not in completed_quest_ids for quest_id in conditions.required_completed_quest_ids):
            return "required_quest_missing"
        if conditions.required_location_ids and current_location_id not in set(conditions.required_location_ids):
            return "required_location_missing"
        return "locked"

    def _is_unlockable(
        self,
        *,
        recipe: CraftingRecipeDefinition,
        world_flags: set[str],
        completed_quest_ids: set[str],
        current_location_id: str | None,
    ) -> bool:
        conditions = self._normalized_conditions(recipe)
        if any(flag_id not in world_flags for flag_id in conditions.required_flags):
            return False
        if any(quest_id not in completed_quest_ids for quest_id in conditions.required_completed_quest_ids):
            return False
        if conditions.required_location_ids and current_location_id not in set(conditions.required_location_ids):
            return False
        return True

    def _normalized_conditions(self, recipe: CraftingRecipeDefinition) -> RecipeUnlockConditions:
        if recipe.unlock_conditions is not None:
            return recipe.unlock_conditions
        if recipe.unlock_flags:
            return RecipeUnlockConditions(required_flags=recipe.unlock_flags)
        return RecipeUnlockConditions()


class RecipeDiscoveryService:
    def __init__(self, definitions: tuple[RecipeDiscoveryDefinition, ...], valid_recipe_ids: set[str]) -> None:
        self._definitions = definitions
        self._valid_recipe_ids = valid_recipe_ids
        self._by_source: dict[tuple[str, str], tuple[RecipeDiscoveryDefinition, ...]] = {}
        self._by_item_id: dict[str, tuple[RecipeDiscoveryDefinition, ...]] = {}
        self._validate_and_index()

    def discover_by_source(
        self,
        *,
        unlock_source_type: str,
        source_id: str,
        discovered_recipe_ids: set[str],
        discovered_recipe_book_ids: set[str],
        unlocked_recipe_ids: set[str],
    ) -> tuple[list[str], list[str], list[str]]:
        discovered_logs: list[str] = []
        already_known_logs: list[str] = []
        warnings: list[str] = []
        for definition in self._by_source.get((unlock_source_type, source_id), tuple()):
            logs = self._apply_definition(
                definition=definition,
                discovered_recipe_ids=discovered_recipe_ids,
                discovered_recipe_book_ids=discovered_recipe_book_ids,
                unlocked_recipe_ids=unlocked_recipe_ids,
            )
            discovered_logs.extend(logs[0])
            already_known_logs.extend(logs[1])
            warnings.extend(logs[2])
        return discovered_logs, already_known_logs, warnings

    def discover_from_items(
        self,
        *,
        gained_item_ids: set[str],
        discovered_recipe_ids: set[str],
        discovered_recipe_book_ids: set[str],
        unlocked_recipe_ids: set[str],
    ) -> tuple[list[str], list[str], list[str]]:
        discovered_logs: list[str] = []
        already_known_logs: list[str] = []
        warnings: list[str] = []
        for item_id in sorted(gained_item_ids):
            for definition in self._by_item_id.get(item_id, tuple()):
                logs = self._apply_definition(
                    definition=definition,
                    discovered_recipe_ids=discovered_recipe_ids,
                    discovered_recipe_book_ids=discovered_recipe_book_ids,
                    unlocked_recipe_ids=unlocked_recipe_ids,
                )
                discovered_logs.extend(logs[0])
                already_known_logs.extend(logs[1])
                warnings.extend(logs[2])
        return discovered_logs, already_known_logs, warnings

    def _apply_definition(
        self,
        *,
        definition: RecipeDiscoveryDefinition,
        discovered_recipe_ids: set[str],
        discovered_recipe_book_ids: set[str],
        unlocked_recipe_ids: set[str],
    ) -> tuple[list[str], list[str], list[str]]:
        discovered_logs: list[str] = []
        already_known_logs: list[str] = []
        warnings: list[str] = []

        if definition.recipe_book_id:
            if definition.recipe_book_id in discovered_recipe_book_ids:
                already_known_logs.append(f"recipe_book_already_known:{definition.recipe_book_id}")
            else:
                discovered_recipe_book_ids.add(definition.recipe_book_id)
                discovered_logs.append(f"recipe_book_discovered:{definition.recipe_book_id}")

        for recipe_id in definition.recipe_ids:
            if recipe_id not in self._valid_recipe_ids:
                warnings.append(f"recipe_discovery_invalid_recipe_id:{recipe_id}")
                continue
            if recipe_id in discovered_recipe_ids:
                already_known_logs.append(f"recipe_already_known:{recipe_id}")
                continue
            discovered_recipe_ids.add(recipe_id)
            unlocked_recipe_ids.add(recipe_id)
            message = definition.unlock_message or f"recipe_discovered:{recipe_id}"
            discovered_logs.append(f"recipe_discovered:{recipe_id}:{message}")
        return discovered_logs, already_known_logs, warnings

    def _validate_and_index(self) -> None:
        for definition in self._definitions:
            if not definition.source_id:
                raise ValueError("recipe discovery source_id is required")
            if not definition.recipe_ids:
                raise ValueError(f"recipe discovery recipe_ids is required source={definition.source_id}")
            for recipe_id in definition.recipe_ids:
                if recipe_id not in self._valid_recipe_ids:
                    raise ValueError(f"recipe discovery has unknown recipe_id={recipe_id}")
            source_key = (definition.unlock_source_type, definition.source_id)
            self._by_source[source_key] = self._by_source.get(source_key, tuple()) + (definition,)
            if definition.unlock_source_type == "loot_item":
                self._by_item_id[definition.source_id] = self._by_item_id.get(definition.source_id, tuple()) + (definition,)
