from __future__ import annotations

import json
from pathlib import Path

from game.quest.domain.entities import (
    EventDefinition,
    EventStep,
    EventStepAction,
    ObjectiveDefinition,
    QuestDefinition,
    QuestReward,
)


class QuestMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_quests(self) -> dict[str, QuestDefinition]:
        raw = json.loads((self._root / "quests.sample.json").read_text(encoding="utf-8"))
        definitions: dict[str, QuestDefinition] = {}
        for quest in raw:
            self._validate_quest(quest)
            objectives = tuple(
                ObjectiveDefinition(
                    id=objective["id"],
                    objective_type=objective["type"],
                    target_enemy_id=objective["target_enemy_id"],
                    required_count=int(objective["required_count"]),
                )
                for objective in quest["objectives"]
            )
            reward_block = quest["reward"]
            definitions[quest["id"]] = QuestDefinition(
                id=quest["id"],
                title=quest["title"],
                description=quest["description"],
                objectives=objectives,
                reward=QuestReward(
                    exp=int(reward_block.get("exp", 0)),
                    gold=int(reward_block.get("gold", 0)),
                    completion_flag=reward_block.get("completion_flag"),
                ),
            )
        return definitions

    def load_events(self) -> dict[str, EventDefinition]:
        raw = json.loads((self._root / "events.sample.json").read_text(encoding="utf-8"))
        definitions: dict[str, EventDefinition] = {}
        for event in raw:
            self._validate_event(event)
            steps = []
            for step in event["steps"]:
                action_raw = step.get("action")
                action = None
                if action_raw is not None:
                    action = EventStepAction(
                        action_type=action_raw["type"],
                        params={k: str(v) for k, v in action_raw.get("params", {}).items()},
                    )
                steps.append(
                    EventStep(
                        id=step["id"],
                        speaker=step.get("speaker"),
                        line=step.get("line"),
                        action=action,
                    )
                )
            definitions[event["id"]] = EventDefinition(
                id=event["id"],
                title=event["title"],
                steps=tuple(steps),
            )
        return definitions

    def _validate_quest(self, quest: dict) -> None:
        required = ["id", "title", "description", "objectives", "reward"]
        for field in required:
            if field not in quest:
                raise ValueError(f"quests.sample.json missing field={field} quest={quest.get('id')}")
        for objective in quest["objectives"]:
            for field in ["id", "type", "target_enemy_id", "required_count"]:
                if field not in objective:
                    raise ValueError(
                        "quests.sample.json objective missing "
                        f"field={field} quest={quest['id']} objective={objective.get('id')}"
                    )

    def _validate_event(self, event: dict) -> None:
        required = ["id", "title", "steps"]
        for field in required:
            if field not in event:
                raise ValueError(f"events.sample.json missing field={field} event={event.get('id')}")
        for step in event["steps"]:
            if "id" not in step:
                raise ValueError(f"events.sample.json step missing id event={event['id']}")
