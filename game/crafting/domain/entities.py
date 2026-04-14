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
