from __future__ import annotations

import json
from pathlib import Path

from game.location.domain.field_event_entities import (
    FieldEventChoiceDefinition,
    FieldEventDefinition,
    FieldEventOutcomeDefinition,
)


class FieldEventMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_events(self) -> dict[str, FieldEventDefinition]:
        raw = json.loads((self._root / "location_events_branching.sample.json").read_text(encoding="utf-8"))
        definitions: dict[str, FieldEventDefinition] = {}
        for row in raw:
            for field in ["event_id", "location_id", "name", "description", "trigger_type", "choices"]:
                if field not in row:
                    raise ValueError(f"location_events_branching.sample.json missing field={field}")
            choices: list[FieldEventChoiceDefinition] = []
            for choice_raw in row["choices"]:
                for field in ["choice_id", "text", "outcomes"]:
                    if field not in choice_raw:
                        raise ValueError(f"location_events_branching.sample.json choice missing field={field}")
                outcomes: list[FieldEventOutcomeDefinition] = []
                for outcome_raw in choice_raw["outcomes"]:
                    if "outcome_type" not in outcome_raw:
                        raise ValueError("location_events_branching.sample.json outcome missing field=outcome_type")
                    outcomes.append(
                        FieldEventOutcomeDefinition(
                            outcome_type=str(outcome_raw["outcome_type"]),
                            params={str(k): str(v) for k, v in outcome_raw.get("params", {}).items()},
                        )
                    )
                if not outcomes:
                    raise ValueError(
                        "location_events_branching.sample.json choice requires at least one outcome"
                    )
                choices.append(
                    FieldEventChoiceDefinition(
                        choice_id=str(choice_raw["choice_id"]),
                        text=str(choice_raw["text"]),
                        outcomes=tuple(outcomes),
                    )
                )
            if not choices:
                raise ValueError("location_events_branching.sample.json event requires at least one choice")
            event_id = str(row["event_id"])
            definitions[event_id] = FieldEventDefinition(
                event_id=event_id,
                location_id=str(row["location_id"]),
                name=str(row["name"]),
                description=str(row["description"]),
                trigger_type=str(row["trigger_type"]),
                repeatable=bool(row.get("repeatable", False)),
                required_flags=tuple(str(flag_id) for flag_id in row.get("required_flags", [])),
                excluded_flags=tuple(str(flag_id) for flag_id in row.get("excluded_flags", [])),
                choices=tuple(choices),
            )
        return definitions
