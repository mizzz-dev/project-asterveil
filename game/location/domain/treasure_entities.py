from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TreasureContentDefinition:
    content_type: str
    item_id: str | None = None
    equipment_id: str | None = None
    recipe_book_id: str | None = None
    quantity: int = 1

    @property
    def inventory_item_id(self) -> str:
        return self.item_id or self.equipment_id or self.recipe_book_id or ""


@dataclass(frozen=True)
class TreasureNodeDefinition:
    reward_node_id: str
    location_id: str
    name: str
    node_type: str
    description: str
    contents: tuple[TreasureContentDefinition, ...]
    one_time: bool = True
    required_flags: tuple[str, ...] = tuple()
    required_facility_id: str | None = None
    required_facility_level: int = 0
    message_on_open: str = ""


@dataclass(frozen=True)
class TreasureNodeStatus:
    reward_node_id: str
    location_id: str
    name: str
    node_type: str
    can_open: bool
    reason_code: str
    is_opened: bool


@dataclass(frozen=True)
class TreasureResult:
    success: bool
    code: str
    message: str
    reward_node_id: str
    gained_items: dict[str, int] = field(default_factory=dict)
    content_types: tuple[str, ...] = tuple()
    message_on_open: str = ""
