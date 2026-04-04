from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LocationDefinition:
    location_id: str
    name: str
    location_type: str
    description: str
    accessible_from: tuple[str, ...]
    available_encounter_ids: tuple[str, ...] = tuple()
    default_encounter_id: str | None = None
    can_return_to_hub: bool = True
    unlock_condition: str | None = None


@dataclass
class LocationState:
    current_location_id: str
    unlocked_location_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class TravelResult:
    success: bool
    code: str
    message: str
    destination_id: str | None = None
