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
