from __future__ import annotations

from dataclasses import dataclass

from .entities import BattleResult, QuestBoardStatus, QuestDefinition, QuestState, QuestStatus


@dataclass(frozen=True)
class TurnInItemPlan:
    objective_id: str
    item_id: str
    required: int
    submitted_before: int
    submit_now: int


@dataclass(frozen=True)
class TurnInPlan:
    success: bool
    code: str
    item_plans: tuple[TurnInItemPlan, ...] = tuple()


@dataclass
class QuestProgressService:
    definitions: dict[str, QuestDefinition]

    def create_initial_state(self, quest_id: str) -> QuestState:
        definition = self._get_definition(quest_id)
        progress = {objective.id: 0 for objective in definition.objectives}
        objective_item_progress = {
            objective.id: {item_id: 0 for item_id, _ in objective.required_items}
            for objective in definition.objectives
            if objective.objective_type == "turn_in_items"
        }
        return QuestState(
            quest_id=quest_id,
            objective_progress=progress,
            objective_item_progress=objective_item_progress,
        )

    def reset_for_reaccept(self, state: QuestState) -> QuestState:
        definition = self._get_definition(state.quest_id)
        state.objective_progress = {objective.id: 0 for objective in definition.objectives}
        state.objective_item_progress = {
            objective.id: {item_id: 0 for item_id, _ in objective.required_items}
            for objective in definition.objectives
            if objective.objective_type == "turn_in_items"
        }
        state.reward_claimed = False
        state.repeat_ready = False
        return state

    def accept(self, state: QuestState) -> QuestState:
        if state.status == QuestStatus.NOT_ACCEPTED:
            state.status = QuestStatus.IN_PROGRESS
        return state

    def reaccept(self, state: QuestState) -> QuestState:
        definition = self._get_definition(state.quest_id)
        if not definition.repeatable:
            raise ValueError(f"Quest is not repeatable: {state.quest_id}")
        if state.status != QuestStatus.COMPLETED:
            raise ValueError(f"Quest is not completed: {state.quest_id}")
        if not state.repeat_ready:
            raise ValueError(f"Quest is not ready for reaccept: {state.quest_id}")
        self.reset_for_reaccept(state)
        state.status = QuestStatus.IN_PROGRESS
        return state

    def active_objective(self, state: QuestState):
        if state.status != QuestStatus.IN_PROGRESS:
            return None
        definition = self._get_definition(state.quest_id)
        for objective in self._ordered_objectives(definition):
            if state.objective_progress.get(objective.id, 0) < objective.required_count:
                return objective
        return None

    def active_objective_id(self, state: QuestState) -> str | None:
        objective = self.active_objective(state)
        return None if objective is None else objective.id

    def completed_objective_ids(self, state: QuestState) -> tuple[str, ...]:
        definition = self._get_definition(state.quest_id)
        completed: list[str] = []
        for objective in self._ordered_objectives(definition):
            if state.objective_progress.get(objective.id, 0) >= objective.required_count:
                completed.append(objective.id)
        return tuple(completed)

    def apply_battle_result(self, state: QuestState, battle_result: BattleResult) -> QuestState:
        if state.status != QuestStatus.IN_PROGRESS:
            return state
        if not battle_result.player_won:
            return state

        objective = self.active_objective(state)
        if objective is None or objective.objective_type != "kill_enemy":
            return state
        if objective.target_enemy_id not in battle_result.defeated_enemy_ids:
            return state

        current = state.objective_progress.get(objective.id, 0)
        state.objective_progress[objective.id] = min(objective.required_count, current + 1)
        self._refresh_status(state)
        return state

    def apply_gather_item_progress(self, state: QuestState, gained_items: dict[str, int]) -> list[str]:
        if state.status != QuestStatus.IN_PROGRESS or not gained_items:
            return []
        objective = self.active_objective(state)
        if objective is None or objective.objective_type != "gather_items":
            return []

        current = state.objective_progress.get(objective.id, 0)
        gained = 0
        for item_id, required in objective.required_items:
            if required <= 0:
                continue
            gained += min(required, max(0, int(gained_items.get(item_id, 0))))
        if gained <= 0:
            return []
        state.objective_progress[objective.id] = min(objective.required_count, current + gained)
        return self._build_progress_transition_logs(state, objective.id)

    def apply_recipe_discovery_progress(self, state: QuestState, discovered_recipe_ids: set[str]) -> list[str]:
        if state.status != QuestStatus.IN_PROGRESS or not discovered_recipe_ids:
            return []
        objective = self.active_objective(state)
        if objective is None or objective.objective_type != "discover_recipe":
            return []
        matched = [recipe_id for recipe_id in objective.required_recipe_ids if recipe_id in discovered_recipe_ids]
        if not matched:
            return []
        state.objective_progress[objective.id] = objective.required_count
        logs = [f"quest_recipe_discovered:{state.quest_id}:{objective.id}:{recipe_id}" for recipe_id in matched]
        logs.extend(self._build_progress_transition_logs(state, objective.id))
        return logs

    def apply_craft_item_progress(self, state: QuestState, crafted_items: dict[str, int]) -> list[str]:
        if state.status != QuestStatus.IN_PROGRESS or not crafted_items:
            return []
        objective = self.active_objective(state)
        if objective is None or objective.objective_type != "craft_item":
            return []

        current = state.objective_progress.get(objective.id, 0)
        crafted_count = 0
        for item_id, required in objective.required_items:
            if required <= 0:
                continue
            crafted_count += min(required, max(0, int(crafted_items.get(item_id, 0))))
        if crafted_count <= 0:
            return []
        state.objective_progress[objective.id] = min(objective.required_count, current + crafted_count)
        return self._build_progress_transition_logs(state, objective.id)

    def build_turn_in_plan(self, state: QuestState, inventory_items: dict[str, int]) -> TurnInPlan:
        if state.status != QuestStatus.IN_PROGRESS:
            return TurnInPlan(success=False, code="turn_in_failed:quest_not_in_progress")

        objective = self.active_objective(state)
        if objective is None:
            return TurnInPlan(success=False, code="turn_in_failed:no_active_objective")
        if objective.objective_type != "turn_in_items":
            return TurnInPlan(success=False, code="turn_in_failed:no_turn_in_objective")

        item_plans: list[TurnInItemPlan] = []
        item_progress = state.objective_item_progress.setdefault(
            objective.id,
            {item_id: 0 for item_id, _ in objective.required_items},
        )
        objective_must_block = False

        for item_id, required in objective.required_items:
            submitted_before = int(item_progress.get(item_id, 0))
            remain = max(0, required - submitted_before)
            if remain <= 0:
                continue
            owned = int(inventory_items.get(item_id, 0))
            submit_now = min(remain, owned)
            if submit_now <= 0:
                if not objective.allow_partial_turn_in:
                    objective_must_block = True
                continue
            item_plans.append(
                TurnInItemPlan(
                    objective_id=objective.id,
                    item_id=item_id,
                    required=required,
                    submitted_before=submitted_before,
                    submit_now=submit_now,
                )
            )
            if submit_now < remain and not objective.allow_partial_turn_in:
                objective_must_block = True

        if objective_must_block:
            return TurnInPlan(success=False, code="turn_in_failed:insufficient_items")
        if not item_plans:
            return TurnInPlan(success=False, code="turn_in_failed:no_items_to_turn_in")
        return TurnInPlan(success=True, code="turn_in_ready", item_plans=tuple(item_plans))

    def consume_turn_in_items(self, inventory_state: dict, turn_in_plan: TurnInPlan) -> None:
        if not turn_in_plan.success:
            raise ValueError(f"cannot consume turn-in items: {turn_in_plan.code}")
        items = inventory_state.setdefault("items", {})
        for plan in turn_in_plan.item_plans:
            owned = int(items.get(plan.item_id, 0))
            if owned < plan.submit_now:
                raise ValueError(f"turn-in item insufficient at consume: {plan.item_id}")
            remaining = owned - plan.submit_now
            if remaining > 0:
                items[plan.item_id] = remaining
            else:
                items.pop(plan.item_id, None)

    def apply_turn_in_progress(self, state: QuestState, turn_in_plan: TurnInPlan) -> list[str]:
        if not turn_in_plan.success:
            return [turn_in_plan.code]

        logs: list[str] = []
        for plan in turn_in_plan.item_plans:
            objective_progress = state.objective_item_progress.setdefault(plan.objective_id, {})
            submitted_after = plan.submitted_before + plan.submit_now
            objective_progress[plan.item_id] = submitted_after
            logs.append(
                f"turn_in_success:{state.quest_id}:{plan.objective_id}:{plan.item_id}:"
                f"submitted={submitted_after}/{plan.required}:delta={plan.submit_now}"
            )

        objective = self.active_objective(state)
        if objective is None:
            return logs
        objective_progress = state.objective_item_progress.get(objective.id, {})
        total_required = sum(required for _, required in objective.required_items)
        total_submitted = sum(
            min(required, int(objective_progress.get(item_id, 0)))
            for item_id, required in objective.required_items
        )
        state.objective_progress[objective.id] = total_submitted
        logs.extend(self._build_progress_transition_logs(state, objective.id))
        return logs

    def complete(self, state: QuestState) -> QuestState:
        if state.status != QuestStatus.READY_TO_COMPLETE:
            raise ValueError(f"Quest is not completable: {state.quest_id}")
        state.status = QuestStatus.COMPLETED
        state.reward_claimed = True
        definition = self._get_definition(state.quest_id)
        if definition.repeatable and definition.repeat_reset_rule == "manual_reaccept":
            state.repeat_ready = True
        return state

    def apply_repeat_reset_trigger(self, state: QuestState, trigger: str) -> bool:
        definition = self._get_definition(state.quest_id)
        if not definition.repeatable:
            return False
        if state.status != QuestStatus.COMPLETED:
            return False
        if definition.repeat_reset_rule != trigger:
            return False
        if state.repeat_ready:
            return False
        state.repeat_ready = True
        return True

    def is_objectives_completed(self, state: QuestState) -> bool:
        definition = self._get_definition(state.quest_id)
        for objective in self._ordered_objectives(definition):
            if state.objective_progress.get(objective.id, 0) < objective.required_count:
                return False
        return True

    def _build_progress_transition_logs(self, state: QuestState, objective_id: str) -> list[str]:
        logs: list[str] = []
        definition = self._get_definition(state.quest_id)
        objective_map = {objective.id: objective for objective in definition.objectives}
        objective = objective_map.get(objective_id)
        if objective is None:
            return logs

        if state.objective_progress.get(objective_id, 0) < objective.required_count:
            return logs

        logs.append(f"objective_completed:{state.quest_id}:{objective_id}")
        self._refresh_status(state)
        if state.status == QuestStatus.READY_TO_COMPLETE:
            logs.append(f"quest_ready_to_report:{state.quest_id}")
            logs.append(f"quest_status_changed:{state.quest_id}:{state.status.value}")
            return logs

        next_objective = self.active_objective(state)
        if next_objective is not None:
            logs.append(f"next_objective_unlocked:{state.quest_id}:{next_objective.id}")
        return logs

    def _refresh_status(self, state: QuestState) -> None:
        if self.is_objectives_completed(state):
            state.status = QuestStatus.READY_TO_COMPLETE

    def _ordered_objectives(self, definition: QuestDefinition):
        if not definition.objective_sequence:
            return definition.objectives
        objective_map = {objective.id: objective for objective in definition.objectives}
        return tuple(objective_map[objective_id] for objective_id in definition.objective_sequence)

    def _get_definition(self, quest_id: str) -> QuestDefinition:
        if quest_id not in self.definitions:
            raise ValueError(f"Unknown quest_id: {quest_id}")
        return self.definitions[quest_id]


@dataclass(frozen=True)
class QuestBoardEntry:
    quest_id: str
    title: str
    status: QuestBoardStatus
    can_accept: bool
    objective_progress: dict[str, int]


@dataclass
class QuestBoardService:
    definitions: dict[str, QuestDefinition]
    max_active_quests: int = 2

    def list_entries(
        self,
        quest_states: dict[str, QuestState],
        world_flags: set[str],
        party_level: int,
    ) -> list[QuestBoardEntry]:
        entries: list[QuestBoardEntry] = []
        for quest_id in sorted(self.definitions):
            definition = self.definitions[quest_id]
            state = quest_states.get(quest_id)
            board_status = self.evaluate_status(quest_id, quest_states, world_flags, party_level)
            can_accept = (
                board_status in {QuestBoardStatus.AVAILABLE, QuestBoardStatus.REACCEPTABLE}
                and self.can_accept_more(quest_states)
            )
            entries.append(
                QuestBoardEntry(
                    quest_id=quest_id,
                    title=definition.title,
                    status=board_status,
                    can_accept=can_accept,
                    objective_progress={} if state is None else dict(state.objective_progress),
                )
            )
        return entries

    def can_accept_more(self, quest_states: dict[str, QuestState]) -> bool:
        active_count = sum(1 for state in quest_states.values() if state.status == QuestStatus.IN_PROGRESS)
        return active_count < self.max_active_quests

    def evaluate_status(
        self,
        quest_id: str,
        quest_states: dict[str, QuestState],
        world_flags: set[str],
        party_level: int,
    ) -> QuestBoardStatus:
        state = quest_states.get(quest_id)
        if state is not None:
            if state.status == QuestStatus.COMPLETED:
                definition = self.definitions[quest_id]
                if definition.repeatable:
                    if state.repeat_ready:
                        return QuestBoardStatus.REACCEPTABLE
                    return QuestBoardStatus.REPOST_WAITING
                return QuestBoardStatus.COMPLETED
            if state.status == QuestStatus.READY_TO_COMPLETE:
                return QuestBoardStatus.READY_TO_COMPLETE
            if state.status == QuestStatus.IN_PROGRESS:
                return QuestBoardStatus.IN_PROGRESS

        if not self.is_unlocked(quest_id, quest_states, world_flags, party_level):
            return QuestBoardStatus.LOCKED
        return QuestBoardStatus.AVAILABLE

    def is_unlocked(
        self,
        quest_id: str,
        quest_states: dict[str, QuestState],
        world_flags: set[str],
        party_level: int,
    ) -> bool:
        definition = self.definitions[quest_id]
        availability = definition.availability

        if availability.min_level is not None and party_level < availability.min_level:
            return False
        for required_flag in availability.required_flags:
            if required_flag not in world_flags:
                return False
        for required_quest_id in availability.required_quest_ids:
            required_state = quest_states.get(required_quest_id)
            if required_state is None or required_state.status != QuestStatus.COMPLETED:
                return False
        return True
