from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GatheringLootEntry:
    item_id: str
    quantity: int
    drop_type: str
    chance: float | None = None


@dataclass(frozen=True)
class GatheringNodeDefinition:
    node_id: str
    location_id: str
    name: str
    node_type: str
    description: str
    loot_entries: tuple[GatheringLootEntry, ...]
    repeatable: bool = False
    unlock_flags: tuple[str, ...] = tuple()
    respawn_rule: str = "none"
    respawn_group_id: str | None = None
    respawn_description: str = ""


@dataclass(frozen=True)
class GatheringNodeStatus:
    node_id: str
    location_id: str
    name: str
    node_type: str
    description: str
    can_gather: bool
    reason_code: str
    is_gathered: bool
    respawn_rule: str
    respawn_description: str


@dataclass(frozen=True)
class GatheringResult:
    success: bool
    code: str
    message: str
    node_id: str
    gained_items: dict[str, int] = field(default_factory=dict)
