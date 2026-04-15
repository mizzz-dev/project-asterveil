from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CraftingIngredient:
    item_id: str
    quantity: int


@dataclass(frozen=True)
class CraftingOutput:
    item_id: str | None = None
    equipment_id: str | None = None
    quantity: int = 1

    @property
    def inventory_item_id(self) -> str:
        return self.item_id or self.equipment_id or ""


@dataclass(frozen=True)
class CraftingRecipeDefinition:
    recipe_id: str
    name: str
    category: str
    ingredients: tuple[CraftingIngredient, ...]
    outputs: tuple[CraftingOutput, ...]
    description: str = ""
    unlock_flags: tuple[str, ...] = tuple()
    unlock_conditions: "RecipeUnlockConditions" | None = None
    visible_before_unlock: bool = True
    unlock_message: str = ""


@dataclass(frozen=True)
class RecipeUnlockConditions:
    required_flags: tuple[str, ...] = tuple()
    required_completed_quest_ids: tuple[str, ...] = tuple()
    required_location_ids: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class RecipeAvailabilityStatus:
    recipe_id: str
    unlocked: bool
    can_craft: bool
    visible: bool
    lock_reason: str


@dataclass(frozen=True)
class MaterialRequirementStatus:
    item_id: str
    required: int
    owned: int


@dataclass(frozen=True)
class RecipeResolution:
    can_craft: bool
    missing_materials: tuple[MaterialRequirementStatus, ...]
    required_materials: tuple[MaterialRequirementStatus, ...]
    aggregated_outputs: dict[str, int]


@dataclass(frozen=True)
class CraftingResult:
    success: bool
    code: str
    message: str
    consumed: tuple[MaterialRequirementStatus, ...] = tuple()
    crafted: dict[str, int] | None = None


@dataclass(frozen=True)
class RecipeDiscoveryDefinition:
    recipe_book_id: str | None
    recipe_unlock_event_id: str | None
    recipe_ids: tuple[str, ...]
    unlock_source_type: str
    source_id: str
    unlock_message: str = ""
    category: str = "general"
    workshop_npc_id: str | None = None
