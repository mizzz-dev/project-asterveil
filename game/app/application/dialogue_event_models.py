from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DialogueCondition:
    required_flags: tuple[str, ...] = tuple()
    excluded_flags: tuple[str, ...] = tuple()
    required_quest_status: dict[str, str] = field(default_factory=dict)
    required_location_id: str | None = None


@dataclass(frozen=True)
class DialogueEntry:
    entry_id: str
    priority: int
    lines: tuple[str, ...]
    condition: DialogueCondition = DialogueCondition()
    steps: tuple["DialogueStep", ...] = tuple()


@dataclass(frozen=True)
class DialogueChoiceEffect:
    action_type: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DialogueChoiceDefinition:
    choice_id: str
    text: str
    next_step_id: str
    set_flags: tuple[str, ...] = tuple()
    required_flags: tuple[str, ...] = tuple()
    excluded_flags: tuple[str, ...] = tuple()
    effects: tuple[DialogueChoiceEffect, ...] = tuple()


@dataclass(frozen=True)
class DialogueStep:
    step_id: str
    speaker: str
    lines: tuple[str, ...]
    choices: tuple[DialogueChoiceDefinition, ...] = tuple()


@dataclass(frozen=True)
class NpcDialogueDefinition:
    npc_id: str
    npc_name: str
    location_id: str
    dialogue_entries: tuple[DialogueEntry, ...]
    fallback_lines: tuple[str, ...]


@dataclass(frozen=True)
class DialogueResolutionResult:
    success: bool
    code: str
    npc_id: str
    npc_name: str
    lines: tuple[str, ...]
    matched_entry_id: str | None = None
    entry: DialogueEntry | None = None


@dataclass(frozen=True)
class DialogueChoiceResult:
    success: bool
    code: str
    selected_choice_id: str | None = None
    next_step_id: str | None = None
    set_flags: tuple[str, ...] = tuple()
    effects: tuple[DialogueChoiceEffect, ...] = tuple()


@dataclass(frozen=True)
class LocationEventCondition:
    required_flags: tuple[str, ...] = tuple()
    excluded_flags: tuple[str, ...] = tuple()
    required_quest_status: dict[str, str] = field(default_factory=dict)
    required_location_id: str | None = None


@dataclass(frozen=True)
class LocationEventAction:
    action_type: str
    params: dict[str, str]


@dataclass(frozen=True)
class LocationEventDefinition:
    event_id: str
    trigger_type: str
    location_id: str
    priority: int
    repeatable: bool
    condition: LocationEventCondition
    dialogue_lines: tuple[str, ...] = tuple()
    actions: tuple[LocationEventAction, ...] = tuple()
