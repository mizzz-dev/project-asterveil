from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from game.quest.domain.entities import BattleResult, EventDefinition, QuestState
from game.quest.domain.services import QuestProgressService


BattleExecutor = Callable[[str], BattleResult]


@dataclass
class QuestSliceSession:
    quest_service: QuestProgressService
    events: dict[str, EventDefinition]
    battle_executor: BattleExecutor
    quest_states: dict[str, QuestState] = field(default_factory=dict)
    world_flags: set[str] = field(default_factory=set)

    def play_event(self, event_id: str) -> list[str]:
        if event_id not in self.events:
            raise ValueError(f"Unknown event_id: {event_id}")

        logs: list[str] = [f"event_start:{event_id}"]
        event = self.events[event_id]
        for step in event.steps:
            if step.line:
                speaker = step.speaker or "narration"
                logs.append(f"line:{speaker}:{step.line}")
            if step.action is None:
                continue
            logs.extend(self._run_action(step.action.action_type, step.action.params))

        logs.append(f"event_end:{event_id}")
        return logs

    def _run_action(self, action_type: str, params: dict[str, str]) -> list[str]:
        if action_type == "accept_quest":
            quest_id = params["quest_id"]
            state = self.quest_states.get(quest_id) or self.quest_service.create_initial_state(quest_id)
            self.quest_states[quest_id] = self.quest_service.accept(state)
            return [f"quest_accepted:{quest_id}"]

        if action_type == "start_battle":
            encounter_id = params["encounter_id"]
            battle_result = self.battle_executor(encounter_id)
            action_logs = [f"battle_finished:{encounter_id}:player_won={battle_result.player_won}"]
            for quest_id, state in self.quest_states.items():
                before = state.status
                self.quest_service.apply_battle_result(state, battle_result)
                if before != state.status:
                    action_logs.append(f"quest_status_changed:{quest_id}:{state.status.value}")
            return action_logs

        if action_type == "set_flag":
            flag_id = params["flag_id"]
            self.world_flags.add(flag_id)
            return [f"flag_set:{flag_id}"]

        if action_type == "complete_quest":
            quest_id = params["quest_id"]
            state = self.quest_states[quest_id]
            self.quest_service.complete(state)
            reward = self.quest_service.definitions[quest_id].reward
            logs = [
                f"quest_completed:{quest_id}",
                f"reward_granted:{quest_id}:exp={reward.exp}:gold={reward.gold}",
            ]
            if reward.completion_flag:
                self.world_flags.add(reward.completion_flag)
                logs.append(f"flag_set:{reward.completion_flag}")
            return logs

        if action_type == "end_event":
            return ["event_step_end"]

        raise ValueError(f"Unsupported event action: {action_type}")
