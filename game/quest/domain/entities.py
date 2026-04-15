from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QuestStatus(str, Enum):
    NOT_ACCEPTED = "not_accepted"
    IN_PROGRESS = "in_progress"
    READY_TO_COMPLETE = "ready_to_complete"
    COMPLETED = "completed"


class QuestBoardStatus(str, Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    READY_TO_COMPLETE = "ready_to_complete"
    COMPLETED = "completed"
    REPOST_WAITING = "repost_waiting"
    REACCEPTABLE = "reacceptable"


@dataclass(frozen=True)
class ObjectiveDefinition:
    id: str
    objective_type: str
    target_enemy_id: str | None = None
    required_count: int = 0
    required_items: tuple[tuple[str, int], ...] = tuple()
    allow_partial_turn_in: bool = False


@dataclass(frozen=True)
class QuestReward:
    exp: int
    gold: int
    items: tuple[tuple[str, int], ...] = tuple()
    completion_flag: str | None = None


@dataclass(frozen=True)
class QuestAvailability:
    required_quest_ids: tuple[str, ...] = tuple()
    required_flags: tuple[str, ...] = tuple()
    min_level: int | None = None


@dataclass(frozen=True)
class QuestDefinition:
    id: str
    title: str
    description: str
    objectives: tuple[ObjectiveDefinition, ...]
    reward: QuestReward
    availability: QuestAvailability = QuestAvailability()
    reporting_npc_id: str = "npc.quest.board"
    category: str | None = None
    repeatable: bool = False
    repeat_reset_rule: str = "manual_reaccept"
    repeat_category: str | None = None
    reaccept_message: str | None = None
    encounter_id: str | None = None
    target_location_id: str | None = None


@dataclass
class QuestState:
    quest_id: str
    status: QuestStatus = QuestStatus.NOT_ACCEPTED
    objective_progress: dict[str, int] = field(default_factory=dict)
    objective_item_progress: dict[str, dict[str, int]] = field(default_factory=dict)
    reward_claimed: bool = False
    repeat_ready: bool = False


@dataclass(frozen=True)
class BattleResult:
    encounter_id: str
    player_won: bool
    defeated_enemy_ids: tuple[str, ...]


@dataclass(frozen=True)
class EventStepAction:
    action_type: str
    params: dict[str, str]


@dataclass(frozen=True)
class EventStep:
    id: str
    speaker: str | None
    line: str | None
    action: EventStepAction | None = None


@dataclass(frozen=True)
class EventDefinition:
    id: str
    title: str
    steps: tuple[EventStep, ...]
