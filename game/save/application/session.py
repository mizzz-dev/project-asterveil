from __future__ import annotations

from dataclasses import dataclass

from game.quest.application.session import QuestSliceSession
from game.quest.domain.entities import QuestState, QuestStatus
from game.save.domain.entities import (
    SAVE_VERSION,
    PartyMemberState,
    PlayerProfileState,
    QuestSaveState,
    SaveData,
)


@dataclass
class SaveSliceApplicationService:
    def build_save_data(
        self,
        quest_session: QuestSliceSession,
        party_members: list[PartyMemberState],
        last_event_id: str | None,
        difficulty: str = "standard",
        play_time_sec: int = 0,
        inventory_state: dict | None = None,
        meta: dict | None = None,
    ) -> SaveData:
        quest_state: dict[str, QuestSaveState] = {}
        for quest_id, state in quest_session.quest_states.items():
            definition = quest_session.quest_service.definitions[quest_id]
            ordered_progress = [state.objective_progress.get(objective.id, 0) for objective in definition.objectives]
            ordered_item_progress = [dict(state.objective_item_progress.get(objective.id, {})) for objective in definition.objectives]
            quest_state[quest_id] = QuestSaveState(
                status=state.status.value,
                objective_progress=ordered_progress,
                objective_item_progress=ordered_item_progress,
                reward_claimed=state.reward_claimed,
            )

        world_flags = {flag_id: True for flag_id in sorted(quest_session.world_flags)}
        progression: dict[str, str] = {}
        if last_event_id is not None:
            progression["last_event_id"] = last_event_id

        return SaveData(
            save_version=SAVE_VERSION,
            player_profile=PlayerProfileState(
                difficulty=difficulty,
                play_time_sec=play_time_sec,
            ),
            party_members=party_members,
            quest_state=quest_state,
            world_flags=world_flags,
            progression=progression,
            inventory_state=inventory_state or {},
            meta=meta or {},
        )

    def restore_quest_session(self, quest_session: QuestSliceSession, save_data: SaveData) -> str | None:
        restored_quests: dict[str, QuestState] = {}
        for quest_id, quest_save in save_data.quest_state.items():
            definition = quest_session.quest_service.definitions.get(quest_id)
            if definition is None:
                raise ValueError(f"save_data has unknown quest_id={quest_id}")
            if len(quest_save.objective_progress) != len(definition.objectives):
                raise ValueError(f"objective_progress length mismatch quest_id={quest_id}")

            objective_progress = {
                objective.id: quest_save.objective_progress[index]
                for index, objective in enumerate(definition.objectives)
            }
            objective_item_progress = {
                objective.id: dict(quest_save.objective_item_progress[index])
                for index, objective in enumerate(definition.objectives)
                if index < len(quest_save.objective_item_progress)
            }
            restored_quests[quest_id] = QuestState(
                quest_id=quest_id,
                status=QuestStatus(quest_save.status),
                objective_progress=objective_progress,
                objective_item_progress=objective_item_progress,
                reward_claimed=quest_save.reward_claimed,
            )

        quest_session.quest_states = restored_quests
        quest_session.world_flags = {flag_id for flag_id, enabled in save_data.world_flags.items() if bool(enabled)}
        return save_data.progression.get("last_event_id")
