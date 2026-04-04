from __future__ import annotations

import json
from pathlib import Path

from game.location.domain.entities import LocationDefinition


class LocationMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_locations(self) -> dict[str, LocationDefinition]:
        raw = json.loads((self._root / "locations.sample.json").read_text(encoding="utf-8"))
        definitions: dict[str, LocationDefinition] = {}
        for row in raw:
            for field in ["location_id", "name", "location_type", "description", "accessible_from"]:
                if field not in row:
                    raise ValueError(f"locations.sample.json missing field={field}")

            location_id = str(row["location_id"])
            accessible_from = tuple(str(src) for src in row.get("accessible_from", []))
            available_encounters = tuple(str(eid) for eid in row.get("available_encounter_ids", []))
            default_encounter_id = row.get("default_encounter_id")
            if default_encounter_id is not None:
                default_encounter_id = str(default_encounter_id)

            definitions[location_id] = LocationDefinition(
                location_id=location_id,
                name=str(row["name"]),
                location_type=str(row["location_type"]),
                description=str(row["description"]),
                accessible_from=accessible_from,
                available_encounter_ids=available_encounters,
                default_encounter_id=default_encounter_id,
                can_return_to_hub=bool(row.get("can_return_to_hub", True)),
                unlock_condition=(str(row["unlock_condition"]) if row.get("unlock_condition") else None),
            )
        return definitions
