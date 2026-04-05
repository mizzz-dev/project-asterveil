from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Team(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"


@dataclass(frozen=True)
class Stats:
    hp: int
    atk: int
    defense: int
    spd: int


@dataclass(frozen=True)
class SkillDefinition:
    id: str
    target_type: str
    sp_cost: int
    power: float
    apply_effect_ids: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class StatusEffectDefinition:
    effect_id: str
    name: str
    effect_type: str
    target_stat: str
    magnitude: float
    duration_turns: int
    application_rule: str
    clear_on_rest: bool
    removable_by_item: bool
    description: str


@dataclass
class ActiveEffectState:
    effect_id: str
    remaining_turns: int


@dataclass(frozen=True)
class UnitDefinition:
    id: str
    team: Team
    stats: Stats
    skill_ids: tuple[str, ...]


@dataclass
class CombatantState:
    unit_id: str
    team: Team
    max_hp: int
    hp: int
    atk: int
    defense: int
    spd: int
    sp: int = 0
    alive: bool = True
    active_effects: list[ActiveEffectState] = None

    def __post_init__(self) -> None:
        if self.active_effects is None:
            self.active_effects = []

    def apply_damage(self, amount: int) -> int:
        if not self.alive:
            return 0
        actual = max(0, amount)
        self.hp = max(0, self.hp - actual)
        if self.hp <= 0:
            self.alive = False
        return actual


@dataclass(frozen=True)
class ActionCommand:
    actor_id: str
    action_type: str  # attack | skill
    target_id: str
    skill_id: str | None = None


@dataclass(frozen=True)
class ActionResult:
    actor_id: str
    target_id: str
    action_type: str
    skill_id: str | None
    damage: int
    target_hp_after: int
    target_alive: bool
    logs: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class TurnResult:
    acted: bool
    actor_id: str | None
    summary: ActionResult | None
    winner: Team | None
    logs: tuple[str, ...] = tuple()
