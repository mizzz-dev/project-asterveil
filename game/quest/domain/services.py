from __future__ import annotations

from dataclasses import dataclass

from .entities import BattleResult, QuestBoardStatus, QuestDefinition, QuestState, QuestStatus


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
                board_status == QuestBoardStatus.AVAILABLE
                and self.can_accept_more(quest_states)
                and not definition.repeatable
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
