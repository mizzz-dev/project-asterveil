from __future__ import annotations

from dataclasses import dataclass

from game.app.application.dialogue_event_models import (
    DialogueResolutionResult,
    LocationEventDefinition,
    NpcDialogueDefinition,
)
from game.quest.domain.entities import QuestState


@dataclass
class DialogueService:
    npc_definitions: dict[str, NpcDialogueDefinition]

    def list_npcs_by_location(self, location_id: str) -> list[NpcDialogueDefinition]:
        npcs = [npc for npc in self.npc_definitions.values() if npc.location_id == location_id]
        return sorted(npcs, key=lambda npc: npc.npc_id)

    def resolve(
        self,
        npc_id: str,
        current_location_id: str,
        world_flags: set[str],
        quest_states: dict[str, QuestState],
    ) -> DialogueResolutionResult:
        definition = self.npc_definitions.get(npc_id)
        if definition is None:
            return DialogueResolutionResult(
                success=False,
                code="npc_not_found",
                npc_id=npc_id,
                npc_name=npc_id,
                lines=(f"dialogue_failed:npc_not_found:{npc_id}",),
            )
        if definition.location_id != current_location_id:
            return DialogueResolutionResult(
                success=False,
                code="npc_not_in_location",
                npc_id=npc_id,
                npc_name=definition.npc_name,
                lines=(f"dialogue_failed:npc_not_in_location:{npc_id}:{current_location_id}",),
            )

        sorted_entries = sorted(definition.dialogue_entries, key=lambda entry: entry.priority, reverse=True)
        for entry in sorted_entries:
            if self._matches(entry.condition, current_location_id, world_flags, quest_states):
                return DialogueResolutionResult(
                    success=True,
                    code="ok",
                    npc_id=npc_id,
                    npc_name=definition.npc_name,
                    lines=entry.lines,
                    matched_entry_id=entry.entry_id,
                )

        if definition.fallback_lines:
            return DialogueResolutionResult(
                success=True,
                code="fallback",
                npc_id=npc_id,
                npc_name=definition.npc_name,
                lines=definition.fallback_lines,
            )

        return DialogueResolutionResult(
            success=False,
            code="no_dialogue",
            npc_id=npc_id,
            npc_name=definition.npc_name,
            lines=(f"dialogue_failed:no_dialogue:{npc_id}",),
        )

    def _matches(self, condition, current_location_id, world_flags, quest_states) -> bool:
        if condition.required_location_id and condition.required_location_id != current_location_id:
            return False
        for flag_id in condition.required_flags:
            if flag_id not in world_flags:
                return False
        for flag_id in condition.excluded_flags:
            if flag_id in world_flags:
                return False
        for quest_id, expected_status in condition.required_quest_status.items():
            state = quest_states.get(quest_id)
            if state is None or state.status.value != expected_status:
                return False
        return True


@dataclass
class LocationEventService:
    event_definitions: dict[str, LocationEventDefinition]

    def resolve_on_enter(
        self,
        location_id: str,
        world_flags: set[str],
        quest_states: dict[str, QuestState],
        completed_event_ids: set[str],
    ) -> list[LocationEventDefinition]:
        candidates: list[LocationEventDefinition] = []
        for event in self.event_definitions.values():
            if event.trigger_type != "on_enter_location":
                continue
            if event.location_id != location_id:
                continue
            if event.event_id in completed_event_ids and not event.repeatable:
                continue
            if not self._matches(event, location_id, world_flags, quest_states):
                continue
            candidates.append(event)
        return sorted(candidates, key=lambda row: row.priority, reverse=True)

    def _matches(self, event, location_id, world_flags, quest_states) -> bool:
        condition = event.condition
        if condition.required_location_id and condition.required_location_id != location_id:
            return False
        for flag_id in condition.required_flags:
            if flag_id not in world_flags:
                return False
        for flag_id in condition.excluded_flags:
            if flag_id in world_flags:
                return False
        for quest_id, expected_status in condition.required_quest_status.items():
            state = quest_states.get(quest_id)
            if state is None or state.status.value != expected_status:
                return False
        return True
