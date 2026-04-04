from __future__ import annotations

import json
from pathlib import Path

from game.app.application.dialogue_event_models import (
    DialogueCondition,
    DialogueEntry,
    LocationEventAction,
    LocationEventCondition,
    LocationEventDefinition,
    NpcDialogueDefinition,
)


class DialogueEventMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_npc_dialogues(self) -> dict[str, NpcDialogueDefinition]:
        npcs_raw = json.loads((self._root / "npcs.sample.json").read_text(encoding="utf-8"))
        dialogues_raw = json.loads((self._root / "dialogues.sample.json").read_text(encoding="utf-8"))
        dialogues_by_npc: dict[str, list[DialogueEntry]] = {}
        for row in dialogues_raw:
            for field in ["entry_id", "npc_id", "priority", "lines"]:
                if field not in row:
                    raise ValueError(f"dialogues.sample.json missing field={field}")
            condition_raw = row.get("condition", {})
            entry = DialogueEntry(
                entry_id=str(row["entry_id"]),
                priority=int(row.get("priority", 0)),
                lines=tuple(str(line) for line in row.get("lines", [])),
                condition=DialogueCondition(
                    required_flags=tuple(str(value) for value in condition_raw.get("required_flags", [])),
                    excluded_flags=tuple(str(value) for value in condition_raw.get("excluded_flags", [])),
                    required_quest_status={
                        str(quest_id): str(status)
                        for quest_id, status in condition_raw.get("required_quest_status", {}).items()
                    },
                    required_location_id=(
                        str(condition_raw["required_location_id"])
                        if condition_raw.get("required_location_id")
                        else None
                    ),
                ),
            )
            dialogues_by_npc.setdefault(str(row["npc_id"]), []).append(entry)

        definitions: dict[str, NpcDialogueDefinition] = {}
        for row in npcs_raw:
            for field in ["npc_id", "npc_name", "location_id"]:
                if field not in row:
                    raise ValueError(f"npcs.sample.json missing field={field}")
            npc_id = str(row["npc_id"])
            definitions[npc_id] = NpcDialogueDefinition(
                npc_id=npc_id,
                npc_name=str(row["npc_name"]),
                location_id=str(row["location_id"]),
                dialogue_entries=tuple(dialogues_by_npc.get(npc_id, [])),
                fallback_lines=tuple(str(line) for line in row.get("fallback_lines", [])),
            )
        return definitions

    def load_location_events(self) -> dict[str, LocationEventDefinition]:
        raw = json.loads((self._root / "location_events.sample.json").read_text(encoding="utf-8"))
        definitions: dict[str, LocationEventDefinition] = {}
        for row in raw:
            for field in ["event_id", "trigger_type", "location_id"]:
                if field not in row:
                    raise ValueError(f"location_events.sample.json missing field={field}")
            condition_raw = row.get("condition", {})
            actions = tuple(
                LocationEventAction(
                    action_type=str(action.get("action_type")),
                    params={str(k): str(v) for k, v in action.get("params", {}).items()},
                )
                for action in row.get("actions", [])
            )
            event_id = str(row["event_id"])
            definitions[event_id] = LocationEventDefinition(
                event_id=event_id,
                trigger_type=str(row["trigger_type"]),
                location_id=str(row["location_id"]),
                priority=int(row.get("priority", 0)),
                repeatable=bool(row.get("repeatable", False)),
                condition=LocationEventCondition(
                    required_flags=tuple(str(value) for value in condition_raw.get("required_flags", [])),
                    excluded_flags=tuple(str(value) for value in condition_raw.get("excluded_flags", [])),
                    required_quest_status={
                        str(quest_id): str(status)
                        for quest_id, status in condition_raw.get("required_quest_status", {}).items()
                    },
                    required_location_id=(
                        str(condition_raw["required_location_id"])
                        if condition_raw.get("required_location_id")
                        else None
                    ),
                ),
                dialogue_lines=tuple(str(line) for line in row.get("dialogue_lines", [])),
                actions=actions,
            )
        return definitions
