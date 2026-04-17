from __future__ import annotations

from dataclasses import dataclass

from game.location.domain.miniboss_entities import (
    MinibossDefinition,
    MinibossRewardResolution,
    MinibossStartResult,
)


@dataclass
class MinibossService:
    definitions: dict[str, MinibossDefinition]

    def resolve_start(
        self,
        *,
        miniboss_id: str,
        trigger_event_id: str,
        location_id: str,
        defeated_miniboss_ids: set[str],
    ) -> MinibossStartResult:
        definition = self.definitions.get(miniboss_id)
        if definition is None:
            return MinibossStartResult(False, f"miniboss_failed:not_found:{miniboss_id}")
        if definition.trigger_event_id != trigger_event_id:
            return MinibossStartResult(
                False,
                f"miniboss_failed:trigger_mismatch:{miniboss_id}:{trigger_event_id}",
            )
        if definition.location_id != location_id:
            return MinibossStartResult(
                False,
                f"miniboss_failed:location_mismatch:{miniboss_id}:{location_id}",
            )

        is_defeated = miniboss_id in defeated_miniboss_ids
        if is_defeated and not definition.repeatable:
            return MinibossStartResult(
                False,
                f"miniboss_already_defeated:{miniboss_id}:repeatable=false",
                definition=definition,
                is_first_clear=False,
            )
        return MinibossStartResult(
            True,
            "ok",
            definition=definition,
            is_first_clear=not is_defeated,
        )

    def resolve_rewards(
        self,
        *,
        definition: MinibossDefinition,
        is_first_clear: bool,
        first_clear_reward_claimed_ids: set[str],
    ) -> MinibossRewardResolution:
        if is_first_clear and definition.miniboss_id not in first_clear_reward_claimed_ids:
            return MinibossRewardResolution(
                items=definition.first_clear_rewards,
                logs=tuple(
                    f"miniboss_first_clear_reward:{definition.miniboss_id}:{item.item_id}:x{item.amount}"
                    for item in definition.first_clear_rewards
                ),
                grant_first_clear=True,
            )
        if not is_first_clear and definition.repeat_rewards:
            return MinibossRewardResolution(
                items=definition.repeat_rewards,
                logs=tuple(
                    f"miniboss_repeat_reward:{definition.miniboss_id}:{item.item_id}:x{item.amount}"
                    for item in definition.repeat_rewards
                ),
                grant_first_clear=False,
            )
        return MinibossRewardResolution(
            items=tuple(),
            logs=(f"miniboss_reward_skipped:{definition.miniboss_id}",),
            grant_first_clear=False,
        )

    def event_status_label(self, event_id: str, defeated_miniboss_ids: set[str]) -> str | None:
        definition = next((row for row in self.definitions.values() if row.trigger_event_id == event_id), None)
        if definition is None:
            return None
        defeated = definition.miniboss_id in defeated_miniboss_ids
        if defeated and not definition.repeatable:
            return f"field_event_miniboss:{event_id}:{definition.miniboss_id}:{definition.display_name}:[撃破済み][再戦不可]"
        if defeated:
            return f"field_event_miniboss:{event_id}:{definition.miniboss_id}:{definition.display_name}:[撃破済み]"
        return f"field_event_miniboss:{event_id}:{definition.miniboss_id}:{definition.display_name}:[未撃破]"
