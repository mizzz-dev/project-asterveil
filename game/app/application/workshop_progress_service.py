from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkshopOrderDefinition:
    order_id: str
    name: str
    description: str
    repeatable: bool
    repeat_reset_rule: str
    required_turn_in_items: tuple[tuple[str, int], ...]
    require_crafted_item: bool
    workshop_progress_value: int
    required_workshop_level: int
    rewards: dict[str, object]
    unlock_conditions: dict[str, object]


@dataclass(frozen=True)
class WorkshopRankDefinition:
    level: int
    required_progress: int
    unlock_recipe_ids: tuple[str, ...]


@dataclass
class WorkshopProgressState:
    level: int = 1
    progress: int = 0
    unlocked_recipe_ids: set[str] | None = None
    applied_completion_markers: set[str] | None = None

    def __post_init__(self) -> None:
        if self.unlocked_recipe_ids is None:
            self.unlocked_recipe_ids = set()
        if self.applied_completion_markers is None:
            self.applied_completion_markers = set()


class WorkshopProgressService:
    def ensure_initial_unlocks(self, *, state: WorkshopProgressState, rank_definitions: tuple[WorkshopRankDefinition, ...]) -> None:
        for rank in rank_definitions:
            if rank.level > state.level:
                break
            state.unlocked_recipe_ids.update(rank.unlock_recipe_ids)

    def apply_order_completion(
        self,
        *,
        state: WorkshopProgressState,
        order: WorkshopOrderDefinition,
        rank_definitions: tuple[WorkshopRankDefinition, ...],
        completion_marker: str,
    ) -> list[str]:
        if completion_marker in state.applied_completion_markers:
            return [f"workshop_progress_skipped:duplicate_completion:{order.order_id}:{completion_marker}"]
        if order.workshop_progress_value <= 0:
            raise ValueError(f"workshop_order_progress_value_must_be_positive:order_id={order.order_id}")

        state.applied_completion_markers.add(completion_marker)
        prev_progress = state.progress
        state.progress += order.workshop_progress_value
        logs = [
            f"workshop_order_completed:{order.order_id}:progress+={order.workshop_progress_value}",
            f"workshop_progress:{prev_progress}->{state.progress}",
        ]

        logs.extend(self._apply_rank_ups(state=state, rank_definitions=rank_definitions))
        return logs

    def _apply_rank_ups(self, *, state: WorkshopProgressState, rank_definitions: tuple[WorkshopRankDefinition, ...]) -> list[str]:
        logs: list[str] = []
        for rank in rank_definitions:
            if rank.level <= state.level:
                continue
            if state.progress < rank.required_progress:
                break
            prev_level = state.level
            state.level = rank.level
            logs.append(f"workshop_rank_up:{prev_level}->{state.level}")
            for recipe_id in rank.unlock_recipe_ids:
                if recipe_id in state.unlocked_recipe_ids:
                    continue
                state.unlocked_recipe_ids.add(recipe_id)
                logs.append(f"recipe_unlocked_by_workshop_rank:{state.level}:{recipe_id}")
        return logs

    def progress_to_next_rank(
        self,
        *,
        state: WorkshopProgressState,
        rank_definitions: tuple[WorkshopRankDefinition, ...],
    ) -> tuple[int | None, int | None]:
        for rank in rank_definitions:
            if rank.level <= state.level:
                continue
            needed = max(0, rank.required_progress - state.progress)
            return rank.level, needed
        return None, None

    def is_recipe_unlocked(self, *, recipe_id: str, state: WorkshopProgressState, rank_definitions: tuple[WorkshopRankDefinition, ...]) -> bool:
        lock_targets = {recipe_id for rank in rank_definitions for recipe_id in rank.unlock_recipe_ids}
        if recipe_id not in lock_targets:
            return True
        return recipe_id in state.unlocked_recipe_ids
