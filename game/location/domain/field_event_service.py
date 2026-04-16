from __future__ import annotations

from dataclasses import dataclass

from game.location.domain.field_event_entities import (
    FieldEventDefinition,
    FieldEventResolveResult,
    FieldEventStatus,
)


@dataclass
class FieldEventService:
    definitions: dict[str, FieldEventDefinition]

    def list_events_for_location(
        self,
        *,
        location_id: str,
        world_flags: set[str],
        completed_event_ids: set[str],
    ) -> list[FieldEventStatus]:
        statuses: list[FieldEventStatus] = []
        for event in sorted(self.definitions.values(), key=lambda row: row.event_id):
            if event.location_id != location_id:
                continue
            is_completed = event.event_id in completed_event_ids
            if is_completed and not event.repeatable:
                statuses.append(
                    FieldEventStatus(
                        event_id=event.event_id,
                        name=event.name,
                        description=event.description,
                        repeatable=event.repeatable,
                        is_completed=True,
                        can_execute=False,
                        reason_code="already_completed",
                    )
                )
                continue
            if not self._matches_flags(event, world_flags):
                statuses.append(
                    FieldEventStatus(
                        event_id=event.event_id,
                        name=event.name,
                        description=event.description,
                        repeatable=event.repeatable,
                        is_completed=is_completed,
                        can_execute=False,
                        reason_code="condition_not_met",
                    )
                )
                continue
            statuses.append(
                FieldEventStatus(
                    event_id=event.event_id,
                    name=event.name,
                    description=event.description,
                    repeatable=event.repeatable,
                    is_completed=is_completed,
                    can_execute=True,
                    reason_code="ok",
                )
            )
        return statuses

    def resolve_choice(
        self,
        *,
        event_id: str,
        choice_id: str,
        location_id: str,
        world_flags: set[str],
        completed_event_ids: set[str],
    ) -> FieldEventResolveResult:
        event = self.definitions.get(event_id)
        if event is None:
            return FieldEventResolveResult(success=False, code=f"field_event_failed:event_not_found:{event_id}")
        if event.location_id != location_id:
            return FieldEventResolveResult(
                success=False,
                code=f"field_event_failed:location_mismatch:{event_id}:{location_id}",
            )
        if event.event_id in completed_event_ids and not event.repeatable:
            return FieldEventResolveResult(success=False, code=f"field_event_already_completed:{event_id}")
        if not self._matches_flags(event, world_flags):
            return FieldEventResolveResult(success=False, code=f"field_event_failed:condition_not_met:{event_id}")
        choice = next((row for row in event.choices if row.choice_id == choice_id), None)
        if choice is None:
            return FieldEventResolveResult(success=False, code=f"field_event_failed:choice_not_found:{choice_id}")
        return FieldEventResolveResult(
            success=True,
            code="ok",
            event=event,
            choice=choice,
            should_mark_completed=not event.repeatable,
        )

    def _matches_flags(self, event: FieldEventDefinition, world_flags: set[str]) -> bool:
        for flag_id in event.required_flags:
            if flag_id not in world_flags:
                return False
        for flag_id in event.excluded_flags:
            if flag_id in world_flags:
                return False
        return True
