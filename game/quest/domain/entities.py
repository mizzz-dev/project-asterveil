from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QuestStatus(str, Enum):
    NOT_ACCEPTED = "not_accepted"
    IN_PROGRESS = "in_progress"
    READY_TO_COMPLETE = "ready_to_complete"
    COMPLETED = "completed"


@dataclass(frozen=True)
class ObjectiveDefinition:
    id: str
    objective_type: str
    target_enemy_id: str
    required_count: int


@dataclass(frozen=True)
class QuestReward:
    exp: int
    gold: int
    items: tuple[tuple[str, int], ...] = tuple()
    completion_flag: str | None = None


@dataclass(frozen=True)
class QuestDefinition:
    id: str
    title: str
    description: str
    objectives: tuple[ObjectiveDefinition, ...]
    reward: QuestReward


@dataclass
class QuestState:
    quest_id: str
    status: QuestStatus = QuestStatus.NOT_ACCEPTED
    objective_progress: dict[str, int] = field(default_factory=dict)
    reward_claimed: bool = False


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
