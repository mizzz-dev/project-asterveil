from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FacilityRequirement:
    required_completed_quest_ids: tuple[str, ...] = tuple()
    required_flags: tuple[str, ...] = tuple()
    required_turn_in_count: int = 0


@dataclass(frozen=True)
class FacilityUnlock:
    recipe_ids: tuple[str, ...] = tuple()
    shop_stock_ids: tuple[str, ...] = tuple()
    dialogue_flags: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class FacilityLevelDefinition:
    level: int
    description: str
    requirements: FacilityRequirement
    unlocks: FacilityUnlock


@dataclass(frozen=True)
class FacilityDefinition:
    facility_id: str
    facility_type: str
    levels: tuple[FacilityLevelDefinition, ...]


@dataclass(frozen=True)
class FacilityProgressContext:
    completed_quest_ids: set[str]
    world_flags: set[str]
    turn_in_count: int


@dataclass(frozen=True)
class FacilityLevelUpResult:
    facility_id: str
    previous_level: int
    new_level: int
    unlocks: FacilityUnlock


class FacilityProgressService:
    def evaluate_level_up(
        self,
        *,
        definitions: dict[str, FacilityDefinition],
        facility_levels: dict[str, int],
        context: FacilityProgressContext,
    ) -> list[FacilityLevelUpResult]:
        results: list[FacilityLevelUpResult] = []
        for facility_id, definition in sorted(definitions.items()):
            current_level = int(facility_levels.get(facility_id, 0))
            sorted_levels = tuple(sorted(definition.levels, key=lambda row: row.level))
            if not sorted_levels:
                continue
            for level_definition in sorted_levels:
                if level_definition.level <= current_level:
                    continue
                if not self._requirements_met(level_definition.requirements, context):
                    break
                previous_level = current_level
                current_level = level_definition.level
                facility_levels[facility_id] = current_level
                results.append(
                    FacilityLevelUpResult(
                        facility_id=facility_id,
                        previous_level=previous_level,
                        new_level=current_level,
                        unlocks=level_definition.unlocks,
                    )
                )
        return results

    def apply_unlocks(
        self,
        *,
        level_up_results: list[FacilityLevelUpResult],
        unlocked_recipe_ids: set[str],
        unlocked_shop_stock_ids: set[str],
        world_flags: set[str],
    ) -> list[str]:
        logs: list[str] = []
        for result in level_up_results:
            logs.append(
                f"facility_level_up:{result.facility_id}:level={result.previous_level}->{result.new_level}"
            )
            for recipe_id in result.unlocks.recipe_ids:
                if recipe_id in unlocked_recipe_ids:
                    continue
                unlocked_recipe_ids.add(recipe_id)
                logs.append(f"recipe_unlocked_by_facility:{result.facility_id}:{recipe_id}")
            for stock_id in result.unlocks.shop_stock_ids:
                if stock_id in unlocked_shop_stock_ids:
                    continue
                unlocked_shop_stock_ids.add(stock_id)
                logs.append(f"shop_stock_unlocked:{result.facility_id}:{stock_id}")
            for flag_id in result.unlocks.dialogue_flags:
                if flag_id in world_flags:
                    continue
                world_flags.add(flag_id)
                logs.append(f"flag_set:{flag_id}")
        return logs

    def _requirements_met(self, requirement: FacilityRequirement, context: FacilityProgressContext) -> bool:
        if any(quest_id not in context.completed_quest_ids for quest_id in requirement.required_completed_quest_ids):
            return False
        if any(flag_id not in context.world_flags for flag_id in requirement.required_flags):
            return False
        if context.turn_in_count < requirement.required_turn_in_count:
            return False
        return True
