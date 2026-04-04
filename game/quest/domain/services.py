from __future__ import annotations

from dataclasses import dataclass

from .entities import BattleResult, QuestDefinition, QuestState, QuestStatus


@dataclass
class QuestProgressService:
    definitions: dict[str, QuestDefinition]

    def create_initial_state(self, quest_id: str) -> QuestState:
        definition = self._get_definition(quest_id)
        progress = {objective.id: 0 for objective in definition.objectives}
        return QuestState(quest_id=quest_id, objective_progress=progress)

    def accept(self, state: QuestState) -> QuestState:
        if state.status == QuestStatus.NOT_ACCEPTED:
            state.status = QuestStatus.IN_PROGRESS
        return state

    def apply_battle_result(self, state: QuestState, battle_result: BattleResult) -> QuestState:
        if state.status != QuestStatus.IN_PROGRESS:
            return state

        definition = self._get_definition(state.quest_id)
        if not battle_result.player_won:
            return state

        for objective in definition.objectives:
            if objective.objective_type != "kill_enemy":
                continue
            if objective.target_enemy_id not in battle_result.defeated_enemy_ids:
                continue
            current = state.objective_progress.get(objective.id, 0)
            state.objective_progress[objective.id] = min(objective.required_count, current + 1)

        if self.is_objectives_completed(state):
            state.status = QuestStatus.READY_TO_COMPLETE
        return state

    def complete(self, state: QuestState) -> QuestState:
        if state.status != QuestStatus.READY_TO_COMPLETE:
            raise ValueError(f"Quest is not completable: {state.quest_id}")
        state.status = QuestStatus.COMPLETED
        state.reward_claimed = True
        return state

    def is_objectives_completed(self, state: QuestState) -> bool:
        definition = self._get_definition(state.quest_id)
        for objective in definition.objectives:
            if state.objective_progress.get(objective.id, 0) < objective.required_count:
                return False
        return True

    def _get_definition(self, quest_id: str) -> QuestDefinition:
        if quest_id not in self.definitions:
            raise ValueError(f"Unknown quest_id: {quest_id}")
        return self.definitions[quest_id]
