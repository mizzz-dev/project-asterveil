from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkshopStoryUnlockRewards:
    recipe_ids: tuple[str, ...] = tuple()
    quest_ids: tuple[str, ...] = tuple()
    location_ids: tuple[str, ...] = tuple()
    field_event_ids: tuple[str, ...] = tuple()
    flag_ids: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class WorkshopStoryStageDefinition:
    storyline_id: str
    npc_id: str
    required_workshop_level: int
    required_flags: tuple[str, ...]
    dialogue_id: str
    description: str
    unlock_rewards: WorkshopStoryUnlockRewards
    priority: int = 0


@dataclass
class WorkshopStoryState:
    seen_stage_ids: set[str] | None = None
    unlocked_quest_ids: set[str] | None = None
    unlocked_recipe_ids: set[str] | None = None
    unlocked_location_ids: set[str] | None = None
    unlocked_field_event_ids: set[str] | None = None

    def __post_init__(self) -> None:
        if self.seen_stage_ids is None:
            self.seen_stage_ids = set()
        if self.unlocked_quest_ids is None:
            self.unlocked_quest_ids = set()
        if self.unlocked_recipe_ids is None:
            self.unlocked_recipe_ids = set()
        if self.unlocked_location_ids is None:
            self.unlocked_location_ids = set()
        if self.unlocked_field_event_ids is None:
            self.unlocked_field_event_ids = set()


class WorkshopStoryService:
    def resolve_for_npc(
        self,
        *,
        npc_id: str,
        workshop_level: int,
        world_flags: set[str],
        state: WorkshopStoryState,
        stage_definitions: tuple[WorkshopStoryStageDefinition, ...],
    ) -> list[WorkshopStoryStageDefinition]:
        matched: list[WorkshopStoryStageDefinition] = []
        for stage in stage_definitions:
            if stage.npc_id != npc_id:
                continue
            if stage.storyline_id in state.seen_stage_ids:
                continue
            if workshop_level < stage.required_workshop_level:
                continue
            if any(flag_id not in world_flags for flag_id in stage.required_flags):
                continue
            matched.append(stage)
        return sorted(matched, key=lambda row: (row.required_workshop_level, row.priority, row.storyline_id))

    def apply_stage(
        self,
        *,
        stage: WorkshopStoryStageDefinition,
        state: WorkshopStoryState,
        world_flags: set[str],
    ) -> list[str]:
        if stage.storyline_id in state.seen_stage_ids:
            return [f"workshop_story_unlock_skipped:already_seen:{stage.storyline_id}"]
        state.seen_stage_ids.add(stage.storyline_id)
        logs = [
            f"workshop_story_advanced:{stage.storyline_id}:{stage.dialogue_id}",
            f"workshop_story_description:{stage.storyline_id}:{stage.description}",
        ]
        for flag_id in stage.unlock_rewards.flag_ids:
            if flag_id in world_flags:
                continue
            world_flags.add(flag_id)
            logs.append(f"workshop_story_unlock:flag:{flag_id}")
        for quest_id in stage.unlock_rewards.quest_ids:
            if quest_id in state.unlocked_quest_ids:
                continue
            state.unlocked_quest_ids.add(quest_id)
            logs.append(f"new_workshop_order_unlocked:{quest_id}")
        for recipe_id in stage.unlock_rewards.recipe_ids:
            if recipe_id in state.unlocked_recipe_ids:
                continue
            state.unlocked_recipe_ids.add(recipe_id)
            logs.append(f"new_advanced_recipe_unlocked:{recipe_id}")
        for location_id in stage.unlock_rewards.location_ids:
            if location_id in state.unlocked_location_ids:
                continue
            state.unlocked_location_ids.add(location_id)
            logs.append(f"workshop_story_unlock:location:{location_id}")
        for event_id in stage.unlock_rewards.field_event_ids:
            if event_id in state.unlocked_field_event_ids:
                continue
            state.unlocked_field_event_ids.add(event_id)
            logs.append(f"workshop_story_unlock:field_event:{event_id}")
        return logs
