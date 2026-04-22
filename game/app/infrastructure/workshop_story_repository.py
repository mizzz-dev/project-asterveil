from __future__ import annotations

import json
from pathlib import Path

from game.app.application.workshop_story_service import WorkshopStoryStageDefinition, WorkshopStoryUnlockRewards


class WorkshopStoryMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load(
        self,
        *,
        valid_npc_ids: set[str],
        valid_quest_ids: set[str],
        valid_recipe_ids: set[str],
        valid_location_ids: set[str],
        valid_field_event_ids: set[str],
    ) -> tuple[WorkshopStoryStageDefinition, ...]:
        path = self._root / "workshop_story.sample.json"
        if not path.exists():
            return tuple()
        raw = json.loads(path.read_text(encoding="utf-8"))
        definitions: list[WorkshopStoryStageDefinition] = []
        for row in raw:
            storyline_id = str(row.get("storyline_id") or "")
            npc_id = str(row.get("npc_id") or "")
            dialogue_id = str(row.get("dialogue_id") or "")
            if not storyline_id:
                raise ValueError("workshop_story.sample.json missing field=storyline_id")
            if not npc_id:
                raise ValueError(f"workshop_story.sample.json missing field=npc_id storyline_id={storyline_id}")
            if npc_id not in valid_npc_ids:
                raise ValueError(f"workshop_story.sample.json unknown npc_id={npc_id} storyline_id={storyline_id}")
            if not dialogue_id:
                raise ValueError(f"workshop_story.sample.json missing field=dialogue_id storyline_id={storyline_id}")

            rewards_raw = row.get("unlock_rewards", {})
            recipe_ids = tuple(str(value) for value in rewards_raw.get("recipe_ids", []))
            quest_ids = tuple(str(value) for value in rewards_raw.get("quest_ids", []))
            location_ids = tuple(str(value) for value in rewards_raw.get("location_ids", []))
            field_event_ids = tuple(str(value) for value in rewards_raw.get("field_event_ids", []))
            for recipe_id in recipe_ids:
                if recipe_id not in valid_recipe_ids:
                    raise ValueError(
                        f"workshop_story.sample.json unknown unlock recipe_id={recipe_id} storyline_id={storyline_id}"
                    )
            for quest_id in quest_ids:
                if quest_id not in valid_quest_ids:
                    raise ValueError(f"workshop_story.sample.json unknown unlock quest_id={quest_id} storyline_id={storyline_id}")
            for location_id in location_ids:
                if location_id not in valid_location_ids:
                    raise ValueError(
                        f"workshop_story.sample.json unknown unlock location_id={location_id} storyline_id={storyline_id}"
                    )
            for event_id in field_event_ids:
                if event_id not in valid_field_event_ids:
                    raise ValueError(
                        f"workshop_story.sample.json unknown unlock field_event_id={event_id} storyline_id={storyline_id}"
                    )

            definitions.append(
                WorkshopStoryStageDefinition(
                    storyline_id=storyline_id,
                    npc_id=npc_id,
                    required_workshop_level=max(1, int(row.get("required_workshop_level", 1))),
                    required_flags=tuple(str(value) for value in row.get("required_flags", [])),
                    dialogue_id=dialogue_id,
                    description=str(row.get("description") or ""),
                    priority=int(row.get("priority", 0)),
                    unlock_rewards=WorkshopStoryUnlockRewards(
                        recipe_ids=recipe_ids,
                        quest_ids=quest_ids,
                        location_ids=location_ids,
                        field_event_ids=field_event_ids,
                        flag_ids=tuple(str(value) for value in rewards_raw.get("flag_ids", [])),
                    ),
                )
            )
        return tuple(sorted(definitions, key=lambda row: (row.required_workshop_level, row.priority, row.storyline_id)))
