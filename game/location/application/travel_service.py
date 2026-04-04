from __future__ import annotations

from game.location.domain.entities import LocationDefinition, LocationState, TravelResult


class TravelService:
    def __init__(self, locations: dict[str, LocationDefinition], hub_location_id: str) -> None:
        self._locations = locations
        self._hub_location_id = hub_location_id
        if hub_location_id not in locations:
            raise ValueError(f"hub location not found: {hub_location_id}")

    @property
    def hub_location_id(self) -> str:
        return self._hub_location_id

    def list_destinations(self, state: LocationState) -> list[LocationDefinition]:
        current = self._locations.get(state.current_location_id)
        if current is None:
            return []

        destinations: list[LocationDefinition] = []
        for definition in self._locations.values():
            if definition.location_id == state.current_location_id:
                continue
            if definition.location_id not in state.unlocked_location_ids:
                continue
            if self._is_reachable(current, definition):
                destinations.append(definition)
        return sorted(destinations, key=lambda location: location.location_id)

    def travel_to(self, state: LocationState, target_location_id: str) -> TravelResult:
        destination = self._locations.get(target_location_id)
        if destination is None:
            return TravelResult(False, "invalid_location", f"travel_failed:invalid_location:{target_location_id}")
        if target_location_id not in state.unlocked_location_ids:
            return TravelResult(False, "locked", f"travel_failed:locked:{target_location_id}")

        current = self._locations.get(state.current_location_id)
        if current is None:
            return TravelResult(False, "invalid_state", "travel_failed:invalid_current_location")
        if not self._is_reachable(current, destination):
            return TravelResult(False, "unreachable", f"travel_failed:unreachable:{state.current_location_id}->{target_location_id}")

        state.current_location_id = target_location_id
        return TravelResult(True, "ok", f"travel_succeeded:{target_location_id}", target_location_id)

    def location(self, location_id: str) -> LocationDefinition | None:
        return self._locations.get(location_id)

    def resolve_quest_target_location_id(self, encounter_id: str | None, target_location_id: str | None) -> str | None:
        if target_location_id:
            return target_location_id
        if encounter_id is None:
            return None
        for location in self._locations.values():
            if location.default_encounter_id == encounter_id or encounter_id in location.available_encounter_ids:
                return location.location_id
        return None

    def evaluate_unlocks(self, state: LocationState, world_flags: set[str]) -> list[str]:
        unlocked: list[str] = []
        for location in self._locations.values():
            if location.location_id in state.unlocked_location_ids:
                continue
            if location.unlock_condition and location.unlock_condition not in world_flags:
                continue
            state.unlocked_location_ids.add(location.location_id)
            unlocked.append(location.location_id)
        return sorted(unlocked)

    def _is_reachable(self, current: LocationDefinition, destination: LocationDefinition) -> bool:
        if current.location_id in destination.accessible_from:
            return True
        if destination.location_id == self._hub_location_id and current.can_return_to_hub:
            return True
        return False
