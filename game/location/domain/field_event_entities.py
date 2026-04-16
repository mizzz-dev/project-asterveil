from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldEventOutcomeDefinition:
    outcome_type: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FieldEventChoiceDefinition:
    choice_id: str
    text: str
    outcomes: tuple[FieldEventOutcomeDefinition, ...]


@dataclass(frozen=True)
class FieldEventDefinition:
    event_id: str
    location_id: str
    name: str
    description: str
    trigger_type: str
    repeatable: bool
    required_flags: tuple[str, ...] = tuple()
    excluded_flags: tuple[str, ...] = tuple()
    choices: tuple[FieldEventChoiceDefinition, ...] = tuple()


@dataclass(frozen=True)
class FieldEventStatus:
    event_id: str
    name: str
    description: str
    repeatable: bool
    is_completed: bool
    can_execute: bool
    reason_code: str


@dataclass(frozen=True)
class FieldEventResolveResult:
    success: bool
    code: str
    event: FieldEventDefinition | None = None
    choice: FieldEventChoiceDefinition | None = None
    should_mark_completed: bool = False
