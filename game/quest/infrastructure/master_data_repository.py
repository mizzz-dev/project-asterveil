from __future__ import annotations

import json
from pathlib import Path

from game.quest.domain.entities import (
    EventDefinition,
    EventStep,
    EventStepAction,
    ObjectiveDefinition,
    QuestAvailability,
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
            quest_id = quest.get("quest_id", quest["id"])
            objectives = tuple(self._to_objective_definition(quest_id, objective) for objective in quest["objectives"])
            reward_block = quest["reward"]
            availability_raw = quest.get("availability", {})
            definitions[quest_id] = QuestDefinition(
                id=quest_id,
                title=quest["title"],
                description=quest["description"],
                objectives=objectives,
                reward=QuestReward(
                    exp=int(reward_block.get("exp", 0)),
                    gold=int(reward_block.get("gold", 0)),
                    items=tuple(
                        (str(item["item_id"]), int(item["amount"]))
                        for item in reward_block.get("items", [])
                    ),
                    completion_flag=reward_block.get("completion_flag"),
                ),
                availability=QuestAvailability(
                    required_quest_ids=tuple(str(qid) for qid in availability_raw.get("required_quest_ids", [])),
                    required_flags=tuple(str(flag_id) for flag_id in availability_raw.get("required_flags", [])),
                    min_level=(
                        int(availability_raw["min_level"])
                        if availability_raw.get("min_level") is not None
                        else None
                    ),
                ),
                reporting_npc_id=str(quest.get("reporting_npc_id", "npc.quest.board")),
                category=quest.get("category"),
                repeatable=bool(quest.get("repeatable", False)),
                encounter_id=quest.get("encounter_id"),
                target_location_id=quest.get("target_location_id"),
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

    def _to_objective_definition(self, quest_id: str, objective: dict) -> ObjectiveDefinition:
        objective_type = str(objective["type"])
        if objective_type == "kill_enemy":
            return ObjectiveDefinition(
                id=objective["id"],
                objective_type=objective_type,
                target_enemy_id=str(objective["target_enemy_id"]),
                required_count=int(objective["required_count"]),
            )

        if objective_type == "turn_in_items":
            required_items = tuple(
                (str(row["item_id"]), int(row["quantity"]))
                for row in objective.get("required_items", [])
            )
            required_count = int(objective.get("required_count", sum(quantity for _, quantity in required_items)))
            return ObjectiveDefinition(
                id=objective["id"],
                objective_type=objective_type,
                required_count=required_count,
                required_items=required_items,
                allow_partial_turn_in=bool(objective.get("allow_partial_turn_in", False)),
            )

        raise ValueError(
            "quests.sample.json objective has unsupported type="
            f"{objective_type} quest={quest_id} objective={objective.get('id')}"
        )

    def _validate_quest(self, quest: dict) -> None:
        if "id" not in quest and "quest_id" not in quest:
            raise ValueError("quests.sample.json missing field=id/quest_id")

        quest_id = quest.get("quest_id", quest.get("id"))
        required = ["title", "description", "objectives", "reward"]
        for field in required:
            if field not in quest:
                raise ValueError(f"quests.sample.json missing field={field} quest={quest_id}")
        for objective in quest["objectives"]:
            for field in ["id", "type"]:
                if field not in objective:
                    raise ValueError(
                        "quests.sample.json objective missing "
                        f"field={field} quest={quest_id} objective={objective.get('id')}"
                    )
            objective_type = str(objective["type"])
            if objective_type == "kill_enemy":
                for field in ["target_enemy_id", "required_count"]:
                    if field not in objective:
                        raise ValueError(
                            "quests.sample.json objective missing "
                            f"field={field} quest={quest_id} objective={objective.get('id')}"
                        )
            elif objective_type == "turn_in_items":
                if "required_items" not in objective:
                    raise ValueError(
                        "quests.sample.json objective missing field=required_items "
                        f"quest={quest_id} objective={objective.get('id')}"
                    )
                for req in objective["required_items"]:
                    for field in ["item_id", "quantity"]:
                        if field not in req:
                            raise ValueError(
                                "quests.sample.json objective.required_items missing "
                                f"field={field} quest={quest_id} objective={objective.get('id')}"
                            )
            else:
                raise ValueError(
                    "quests.sample.json objective has unsupported type="
                    f"{objective_type} quest={quest_id} objective={objective.get('id')}"
                )
        reward = quest["reward"]
        if "items" in reward:
            for item in reward["items"]:
                for field in ["item_id", "amount"]:
                    if field not in item:
                        raise ValueError(
                            "quests.sample.json reward.items missing "
                            f"field={field} quest={quest_id}"
                        )

    def _validate_event(self, event: dict) -> None:
        required = ["id", "title", "steps"]
        for field in required:
            if field not in event:
                raise ValueError(f"events.sample.json missing field={field} event={event.get('id')}")
        for step in event["steps"]:
            if "id" not in step:
                raise ValueError(f"events.sample.json step missing id event={event['id']}")
