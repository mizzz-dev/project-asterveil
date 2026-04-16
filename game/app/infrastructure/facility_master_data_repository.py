from __future__ import annotations

import json
from pathlib import Path

from game.app.application.facility_progression_service import (
    FacilityDefinition,
    FacilityLevelDefinition,
    FacilityRequirement,
    FacilityUnlock,
)


class FacilityMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_facilities(self) -> dict[str, FacilityDefinition]:
        path = self._root / "hub_facilities.sample.json"
        if not path.exists():
            return {}

        raw = json.loads(path.read_text(encoding="utf-8"))
        facilities: dict[str, FacilityDefinition] = {}
        for row in raw:
            facility_id = str(row.get("facility_id") or "")
            facility_type = str(row.get("facility_type") or "")
            levels_raw = row.get("levels")
            if not facility_id:
                raise ValueError("hub_facilities.sample.json missing field=facility_id")
            if not facility_type:
                raise ValueError(f"hub_facilities.sample.json missing field=facility_type facility_id={facility_id}")
            if not isinstance(levels_raw, list) or not levels_raw:
                raise ValueError(f"hub_facilities.sample.json levels must be non-empty array facility_id={facility_id}")

            levels: list[FacilityLevelDefinition] = []
            for level_row in levels_raw:
                level = int(level_row.get("level", 0))
                if level <= 0:
                    raise ValueError(f"hub_facilities.sample.json level must be >=1 facility_id={facility_id}")
                requirement_raw = level_row.get("requirements", {})
                unlock_raw = level_row.get("unlocks", {})
                levels.append(
                    FacilityLevelDefinition(
                        level=level,
                        description=str(level_row.get("description", "")),
                        requirements=FacilityRequirement(
                            required_completed_quest_ids=tuple(
                                str(value) for value in requirement_raw.get("required_completed_quest_ids", [])
                            ),
                            required_flags=tuple(str(value) for value in requirement_raw.get("required_flags", [])),
                            required_turn_in_count=int(requirement_raw.get("required_turn_in_count", 0)),
                        ),
                        unlocks=FacilityUnlock(
                            recipe_ids=tuple(str(value) for value in unlock_raw.get("recipe_ids", [])),
                            shop_stock_ids=tuple(str(value) for value in unlock_raw.get("shop_stock_ids", [])),
                            dialogue_flags=tuple(str(value) for value in unlock_raw.get("dialogue_flags", [])),
                        ),
                    )
                )

            sorted_levels = sorted(levels, key=lambda entry: entry.level)
            if sorted_levels[0].level != 1:
                raise ValueError(f"hub_facilities.sample.json first level must be 1 facility_id={facility_id}")
            for index in range(1, len(sorted_levels)):
                expected_level = sorted_levels[index - 1].level + 1
                if sorted_levels[index].level != expected_level:
                    raise ValueError(
                        f"hub_facilities.sample.json level must be continuous facility_id={facility_id} level={sorted_levels[index].level}"
                    )
            facilities[facility_id] = FacilityDefinition(
                facility_id=facility_id,
                facility_type=facility_type,
                levels=tuple(sorted_levels),
            )

        return facilities
