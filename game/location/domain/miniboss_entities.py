from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MinibossRewardItem:
    item_id: str
    amount: int


@dataclass(frozen=True)
class MinibossDefinition:
    miniboss_id: str
    encounter_id: str
    location_id: str
    trigger_event_id: str
    display_name: str
    first_clear_rewards: tuple[MinibossRewardItem, ...] = tuple()
    repeat_rewards: tuple[MinibossRewardItem, ...] = tuple()
    defeat_flag: str = ""
    repeatable: bool = False
    description: str = ""


@dataclass(frozen=True)
class MinibossStartResult:
    success: bool
    code: str
    definition: MinibossDefinition | None = None
    is_first_clear: bool = False


@dataclass(frozen=True)
class MinibossRewardResolution:
    items: tuple[MinibossRewardItem, ...] = tuple()
    logs: tuple[str, ...] = tuple()
    grant_first_clear: bool = False


@dataclass
class MinibossRuntimeState:
    defeated_miniboss_ids: set[str] = field(default_factory=set)
    first_clear_reward_claimed_ids: set[str] = field(default_factory=set)
