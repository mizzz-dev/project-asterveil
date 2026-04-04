from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from game.app.application.reward_services import RewardApplicationService
from game.app.infrastructure.master_data_repository import AppMasterDataRepository
from game.quest.application.session import QuestSliceSession
from game.quest.cli.run_quest_slice import build_battle_executor
from game.quest.domain.entities import BattleResult, QuestState, QuestStatus
from game.quest.domain.services import QuestProgressService
from game.quest.infrastructure.master_data_repository import QuestMasterDataRepository
from game.save.application.session import SaveSliceApplicationService
from game.save.domain.entities import PartyMemberState
from game.save.infrastructure.repository import JsonFileSaveRepository


QUEST_ID = "quest.ch01.missing_port_record"
REQUEST_EVENT_ID = "event.ch01.port_request"
REPORT_EVENT_ID = "event.ch01.port_report"
ENCOUNTER_ID = "encounter.ch01.port_wraith"


@dataclass
class ActionItem:
    key: str
    label: str


class PlayableSliceApplication:
    def __init__(
        self,
        master_root: Path,
        save_file_path: Path,
        battle_executor: Callable[[str], BattleResult] | None = None,
    ) -> None:
        self._quest_repo = QuestMasterDataRepository(master_root)
        self._app_master_repo = AppMasterDataRepository(master_root)
        self._save_repo = JsonFileSaveRepository(save_file_path)
        self._save_service = SaveSliceApplicationService()
        self._reward_service = RewardApplicationService()
        self._battle_executor = battle_executor or build_battle_executor(master_root)
        self._item_definitions = self._app_master_repo.load_items()
        self._battle_rewards = self._app_master_repo.load_battle_rewards(set(self._item_definitions))

        self.quest_session: QuestSliceSession | None = None
        self.party_members: list[PartyMemberState] = []
        self.last_event_id: str | None = None
        self.inventory_state: dict = {}

    def new_game(self) -> list[str]:
        self.quest_session = self._build_session()
        self.party_members = self._build_initial_party()
        self.inventory_state = {"gold": 0, "items": {}}
        self.quest_session.world_flags.add("flag.game.new_game_started")
        self.last_event_id = "event.system.new_game_intro"

        return [
            "new_game_started",
            "intro:narration:港町アステルに朝日が差し込む。",
            "intro:guide:長老に話しかけ、依頼を受けよう。",
        ]

    def continue_game(self) -> tuple[bool, str]:
        try:
            save_data = self._save_repo.load()
        except FileNotFoundError:
            return False, "セーブデータが見つかりません。先に New Game を開始してください。"
        except json.JSONDecodeError:
            return False, "セーブデータのJSONが破損しています。"
        except ValueError as exc:
            return False, f"セーブデータの整合性エラー: {exc}"

        self.quest_session = self._build_session()
        self.last_event_id = self._save_service.restore_quest_session(self.quest_session, save_data)
        self.party_members = save_data.party_members
        self.inventory_state = save_data.inventory_state or {"gold": 0, "items": {}}
        return True, "セーブデータをロードしました。"

    def available_actions(self) -> list[ActionItem]:
        if self.quest_session is None:
            return []

        items = [ActionItem("status", "ステータス確認"), ActionItem("inventory", "所持品確認")]
        quest_state = self.quest_session.quest_states.get(QUEST_ID)

        if quest_state is None:
            items.append(ActionItem("talk_npc", "NPCと話す（受注）"))
        elif quest_state.status == QuestStatus.IN_PROGRESS:
            items.append(ActionItem("hunt", "討伐へ進む"))
        elif quest_state.status == QuestStatus.READY_TO_COMPLETE:
            items.append(ActionItem("report", "報告する"))

        items.extend(
            [
                ActionItem("quests", "受注中クエスト確認"),
                ActionItem("save", "セーブする"),
                ActionItem("load", "ロードする"),
                ActionItem("exit", "終了する"),
            ]
        )
        return items

    def perform_action(self, action_key: str) -> list[str]:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")

        if action_key == "status":
            return self._status_lines()
        if action_key == "quests":
            return self._quest_lines()
        if action_key == "inventory":
            return self._inventory_lines()
        if action_key == "talk_npc":
            self.last_event_id = REQUEST_EVENT_ID
            logs = self.quest_session.play_event(REQUEST_EVENT_ID)
            if any(log == f"battle_finished:{ENCOUNTER_ID}:player_won=True" for log in logs):
                battle_reward = self._battle_rewards.get(ENCOUNTER_ID)
                if battle_reward is not None:
                    logs.extend(
                        self._reward_service.apply(
                            battle_reward.rewards_on_win,
                            self.party_members,
                            self.inventory_state,
                        )
                    )
            return logs
        if action_key == "hunt":
            return self._run_hunt()
        if action_key == "report":
            self.last_event_id = REPORT_EVENT_ID
            logs = self.quest_session.play_event(REPORT_EVENT_ID)
            state = self.quest_session.quest_states.get(QUEST_ID)
            if state and state.reward_claimed:
                quest_reward = self.quest_session.quest_service.definitions[QUEST_ID].reward
                logs.extend(
                    self._reward_service.apply(
                        self._reward_service.from_quest_reward(quest_reward),
                        self.party_members,
                        self.inventory_state,
                    )
                )
            return logs
        if action_key == "save":
            self.save_game()
            return ["save_completed"]
        if action_key == "load":
            ok, message = self.continue_game()
            prefix = "load_completed" if ok else "load_failed"
            return [f"{prefix}:{message}"]
        if action_key == "exit":
            return ["exit_selected"]

        raise ValueError(f"不明なアクションです: {action_key}")

    def save_game(self) -> None:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")

        save_data = self._save_service.build_save_data(
            quest_session=self.quest_session,
            party_members=self.party_members,
            last_event_id=self.last_event_id,
            play_time_sec=0,
            inventory_state=self.inventory_state,
            meta={"mode": "playable_vertical_slice"},
        )
        self._save_repo.save(save_data)

    def _run_hunt(self) -> list[str]:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")

        quest_state = self.quest_session.quest_states.get(QUEST_ID)
        if quest_state is None:
            return ["hunt_unavailable:quest_not_accepted"]
        if quest_state.status != QuestStatus.IN_PROGRESS:
            return [f"hunt_unavailable:status={quest_state.status.value}"]

        battle_result = self._battle_executor(ENCOUNTER_ID)
        logs = [f"battle_finished:{ENCOUNTER_ID}:player_won={battle_result.player_won}"]
        if battle_result.player_won:
            battle_reward = self._battle_rewards.get(ENCOUNTER_ID)
            if battle_reward is not None:
                logs.extend(
                    self._reward_service.apply(
                        battle_reward.rewards_on_win,
                        self.party_members,
                        self.inventory_state,
                    )
                )
        for state in self.quest_session.quest_states.values():
            before = state.status
            self.quest_session.quest_service.apply_battle_result(state, battle_result)
            if before != state.status:
                logs.append(f"quest_status_changed:{state.quest_id}:{state.status.value}")

        self.last_event_id = "event.system.hunt"
        self.quest_session.world_flags.add("flag.ch01.port_wraith_battle_seen")
        return logs

    def _build_session(self) -> QuestSliceSession:
        return QuestSliceSession(
            quest_service=QuestProgressService(self._quest_repo.load_quests()),
            events=self._quest_repo.load_events(),
            battle_executor=self._battle_executor,
        )

    def _build_initial_party(self) -> list[PartyMemberState]:
        return [
            PartyMemberState(
                character_id="char.main.rion",
                level=8,
                current_exp=0,
                next_level_exp=450,
                max_hp=120,
                current_hp=120,
                max_sp=100,
                current_sp=100,
                atk=24,
                defense=16,
                spd=18,
                alive=True,
                equipped={"weapon": "equip.weapon.bronze_blade"},
                unlocked_skill_ids=["skill.striker.flare_slash"],
            )
        ]

    def _status_lines(self) -> list[str]:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")

        lines = [
            "location:港町アステル",
            f"party_members:{len(self.party_members)}",
            f"last_event_id:{self.last_event_id}",
            f"gold:{self.inventory_state.get('gold', 0)}",
            f"world_flags:{sorted(self.quest_session.world_flags)}",
        ]
        for member in self.party_members:
            lines.append(
                f"member:{member.character_id}:lv={member.level}:exp={member.current_exp}/{member.next_level_exp}:"
                f"hp={member.current_hp}/{member.max_hp}:sp={member.current_sp}/{member.max_sp}:"
                f"atk={member.atk}:def={member.defense}:spd={member.spd}"
            )
        lines.extend(self._quest_lines())
        return lines

    def _inventory_lines(self) -> list[str]:
        items = self.inventory_state.get("items", {})
        lines = [f"gold:{self.inventory_state.get('gold', 0)}"]
        if not items:
            lines.append("inventory:none")
            return lines
        for item_id, amount in sorted(items.items()):
            item_name = self._item_definitions.get(item_id, {}).get("name", item_id)
            lines.append(f"item:{item_id}:{item_name}:x{amount}")
        return lines

    def _quest_lines(self) -> list[str]:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")
        if not self.quest_session.quest_states:
            return ["quest:none"]

        lines: list[str] = []
        for quest_id, state in sorted(self.quest_session.quest_states.items()):
            lines.append(
                f"quest:{quest_id}:status={state.status.value}:progress={state.objective_progress}:"
                f"reward_claimed={state.reward_claimed}"
            )
        return lines

    def quest_state(self, quest_id: str = QUEST_ID) -> QuestState | None:
        if self.quest_session is None:
            return None
        return self.quest_session.quest_states.get(quest_id)
