from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from game.app.application.equipment_service import EquipmentService, VALID_SLOTS
from game.app.application.inn_service import InnService
from game.app.application.item_use_service import ItemUseService
from game.app.application.reward_services import RewardApplicationService
from game.app.infrastructure.master_data_repository import AppMasterDataRepository
from game.location.application.travel_service import TravelService
from game.location.domain.entities import LocationState
from game.location.infrastructure.master_data_repository import LocationMasterDataRepository
from game.quest.application.session import QuestSliceSession
from game.quest.cli.run_quest_slice import build_battle_executor
from game.quest.domain.entities import BattleResult, QuestBoardStatus, QuestState, QuestStatus
from game.quest.domain.services import QuestBoardService, QuestProgressService
from game.quest.infrastructure.master_data_repository import QuestMasterDataRepository
from game.save.application.session import SaveSliceApplicationService
from game.save.domain.entities import PartyMemberState
from game.save.infrastructure.repository import JsonFileSaveRepository
from game.shop.domain.services import ShopService
from game.shop.infrastructure.master_data_repository import ShopMasterDataRepository


BASE_SHOP_ID = "shop.astel.general_store"
BASE_INN_ID = "inn.astel.seaside_inn"
HUB_LOCATION_ID = "location.town.astel"


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
        self._item_use_service = ItemUseService()
        self._shop_repo = ShopMasterDataRepository(master_root)
        self._location_repo = LocationMasterDataRepository(master_root)
        self._battle_executor = battle_executor or build_battle_executor(master_root)
        self._item_definitions = self._app_master_repo.load_items()
        self._equipment_definitions = self._app_master_repo.load_equipment()
        self._equipment_service = EquipmentService(self._equipment_definitions)
        self._shops = self._shop_repo.load_shops()
        self._shop_service = ShopService(self._shops, self._item_definitions)
        self._inns = self._app_master_repo.load_inns()
        self._inn_service = InnService(self._inns, self._equipment_service)
        self._battle_rewards = self._app_master_repo.load_battle_rewards(set(self._item_definitions))
        self._quest_board_service = QuestBoardService(self._quest_repo.load_quests(), max_active_quests=2)
        self._travel_service = TravelService(self._location_repo.load_locations(), hub_location_id=HUB_LOCATION_ID)

        self.quest_session: QuestSliceSession | None = None
        self.party_members: list[PartyMemberState] = []
        self.last_event_id: str | None = None
        self.inventory_state: dict = {}
        self.location_state = LocationState(current_location_id=HUB_LOCATION_ID, unlocked_location_ids={HUB_LOCATION_ID})

    def new_game(self) -> list[str]:
        self.quest_session = self._build_session()
        self.party_members = self._build_initial_party()
        self.inventory_state = {
            "gold": 300,
            "items": {
                "item.consumable.mini_potion": 3,
                "item.consumable.focus_drop": 2,
                "equip.weapon.bronze_blade": 1,
            },
        }
        self.quest_session.world_flags.add("flag.game.new_game_started")
        self.location_state = LocationState(current_location_id=HUB_LOCATION_ID, unlocked_location_ids={HUB_LOCATION_ID})
        self._travel_service.evaluate_unlocks(self.location_state, self.quest_session.world_flags)
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
        location_meta = save_data.meta.get("location_state", {})
        self.location_state = LocationState(
            current_location_id=str(location_meta.get("current_location_id", HUB_LOCATION_ID)),
            unlocked_location_ids=set(location_meta.get("unlocked_location_ids", [HUB_LOCATION_ID])),
        )
        if HUB_LOCATION_ID not in self.location_state.unlocked_location_ids:
            self.location_state.unlocked_location_ids.add(HUB_LOCATION_ID)
        self._travel_service.evaluate_unlocks(self.location_state, self.quest_session.world_flags)
        return True, "セーブデータをロードしました。"

    def available_actions(self) -> list[ActionItem]:
        if self.quest_session is None:
            return []

        items = [
            ActionItem("status", "ステータス確認"),
            ActionItem("inventory", "所持品確認"),
            ActionItem("use_item", "アイテムを使う"),
            ActionItem("equip", "装備変更"),
            ActionItem("shop", "ショップに行く"),
            ActionItem("inn", "宿屋に泊まる"),
            ActionItem("quest_board", "クエストボードを見る"),
            ActionItem("move", "移動する"),
            ActionItem("current_location", "現在地を確認する"),
        ]
        if self._has_active_quest() and self._location_can_hunt():
            items.append(ActionItem("hunt", "討伐へ進む"))
        if self._has_reportable_quest():
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
        if action_key == "quest_board":
            return self.quest_board_lines()
        if action_key == "move":
            return self.travel_options_lines()
        if action_key == "current_location":
            return self.current_location_lines()
        if action_key == "inventory":
            return self._inventory_lines()
        if action_key == "use_item":
            return self._usable_item_lines()
        if action_key == "equip":
            return self.equipment_overview_lines()
        if action_key == "shop":
            return self.shop_catalog_lines()
        if action_key == "inn":
            return self.inn_info_lines()
        if action_key == "hunt":
            return self._run_hunt()
        if action_key == "report":
            return self.report_ready_quest()
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

    def quest_board_lines(self) -> list[str]:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")
        entries = self._quest_board_service.list_entries(
            self.quest_session.quest_states,
            self.quest_session.world_flags,
            self._party_level(),
        )
        lines = [f"quest_board:max_active={self._quest_board_service.max_active_quests}"]
        for entry in entries:
            lines.append(
                f"quest_board_entry:{entry.quest_id}:{entry.title}:status={entry.status.value}:"
                f"can_accept={entry.can_accept}:progress={entry.objective_progress}"
            )
        return lines

    def accept_quest(self, quest_id: str) -> list[str]:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")

        status = self._quest_board_service.evaluate_status(
            quest_id,
            self.quest_session.quest_states,
            self.quest_session.world_flags,
            self._party_level(),
        )
        if status == QuestBoardStatus.LOCKED:
            return [f"quest_accept_failed:locked:{quest_id}"]
        if status != QuestBoardStatus.AVAILABLE:
            return [f"quest_accept_failed:status={status.value}:{quest_id}"]
        if not self._quest_board_service.can_accept_more(self.quest_session.quest_states):
            return [f"quest_accept_failed:active_limit:{self._quest_board_service.max_active_quests}"]

        state = self.quest_session.quest_states.get(quest_id) or self.quest_session.quest_service.create_initial_state(quest_id)
        self.quest_session.quest_states[quest_id] = self.quest_session.quest_service.accept(state)
        self.last_event_id = f"event.system.quest_accepted:{quest_id}"
        return [f"quest_accepted:{quest_id}"]

    def report_ready_quest(self) -> list[str]:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")
        quest_id = self._ready_to_complete_quest_id()
        if quest_id is None:
            return ["report_unavailable:no_ready_quest"]
        state = self.quest_session.quest_states[quest_id]
        self.quest_session.quest_service.complete(state)
        quest_reward = self.quest_session.quest_service.definitions[quest_id].reward
        logs = [f"quest_completed:{quest_id}"]
        logs.extend(
            self._reward_service.apply(
                self._reward_service.from_quest_reward(quest_reward),
                self.party_members,
                self.inventory_state,
            )
        )
        if quest_reward.completion_flag:
            self.quest_session.world_flags.add(quest_reward.completion_flag)
            logs.append(f"flag_set:{quest_reward.completion_flag}")
        for unlocked in self._travel_service.evaluate_unlocks(self.location_state, self.quest_session.world_flags):
            logs.append(f"location_unlocked:{unlocked}")
        self.last_event_id = f"event.system.quest_report:{quest_id}"
        return logs

    def save_game(self) -> None:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")

        save_data = self._save_service.build_save_data(
            quest_session=self.quest_session,
            party_members=self.party_members,
            last_event_id=self.last_event_id,
            play_time_sec=0,
            inventory_state=self.inventory_state,
            meta={
                "mode": "playable_vertical_slice",
                "location_state": {
                    "current_location_id": self.location_state.current_location_id,
                    "unlocked_location_ids": sorted(self.location_state.unlocked_location_ids),
                },
            },
        )
        self._save_repo.save(save_data)

    def travel_options_lines(self) -> list[str]:
        current = self._travel_service.location(self.location_state.current_location_id)
        lines = [f"current_location:{self.location_state.current_location_id}:{current.name if current else 'unknown'}"]
        for destination in self._travel_service.list_destinations(self.location_state):
            lines.append(
                f"travel_option:{destination.location_id}:{destination.name}:type={destination.location_type}"
            )
        return lines

    def travel_to(self, location_id: str) -> list[str]:
        result = self._travel_service.travel_to(self.location_state, location_id)
        if not result.success:
            return [result.message]
        destination = self._travel_service.location(location_id)
        return [result.message, f"current_location:{location_id}:{destination.name if destination else location_id}"]

    def current_location_lines(self) -> list[str]:
        definition = self._travel_service.location(self.location_state.current_location_id)
        if definition is None:
            return [f"current_location:unknown:{self.location_state.current_location_id}"]
        return [
            f"current_location:{definition.location_id}:{definition.name}:type={definition.location_type}",
            f"location_description:{definition.description}",
        ]

    def use_item(self, item_id: str, target_character_id: str) -> list[str]:
        result = self._item_use_service.use_item(
            item_id=item_id,
            target_character_id=target_character_id,
            item_definitions=self._item_definitions,
            party_members=self.party_members,
            inventory_state=self.inventory_state,
        )
        return [result.message]

    def shop_catalog_lines(self, shop_id: str = BASE_SHOP_ID) -> list[str]:
        ok, message, shop = self._shop_service.list_entries(shop_id)
        if not ok or shop is None:
            return [f"shop_failed:{message}"]

        lines = [f"shop:{shop.shop_id}:{shop.name}", f"gold:{self.inventory_state.get('gold', 0)}"]
        for entry in shop.entries:
            item_name = self._item_definitions.get(entry.item_id, {}).get("name", entry.item_id)
            lines.append(
                f"shop_item:{entry.item_id}:{item_name}:price={entry.price}:stock_type={entry.stock_type}"
            )
        return lines

    def buy_item(self, item_id: str, quantity: int = 1, shop_id: str = BASE_SHOP_ID) -> list[str]:
        result = self._shop_service.purchase(
            inventory_state=self.inventory_state,
            shop_id=shop_id,
            item_id=item_id,
            quantity=quantity,
        )
        return [result.message]

    def inn_info_lines(self, inn_id: str = BASE_INN_ID) -> list[str]:
        inn = self._inn_service.get_inn(inn_id)
        if inn is None:
            return [f"inn_failed:inn_not_found:{inn_id}"]
        return [
            f"inn:{inn.inn_id}:{inn.name}",
            f"inn_stay_price:{inn.stay_price}",
            f"gold:{self.inventory_state.get('gold', 0)}",
            f"inn_policy:revive_knocked_out_members={inn.revive_knocked_out_members}",
            f"inn_description:{inn.description}",
        ]

    def stay_at_inn(self, inn_id: str = BASE_INN_ID) -> list[str]:
        result = self._inn_service.stay(
            inn_id=inn_id,
            party_members=self.party_members,
            inventory_state=self.inventory_state,
        )
        lines = [result.message]
        if result.success:
            lines.extend(self.party_member_lines())
        return lines

    def equipment_overview_lines(self) -> list[str]:
        lines = ["equipment:members"]
        lines.extend(self.party_member_lines())
        return lines

    def equippable_options(self, character_id: str, slot_type: str) -> list[tuple[str, str]]:
        member = next((m for m in self.party_members if m.character_id == character_id), None)
        if member is None or slot_type not in VALID_SLOTS:
            return []
        options = [("cancel", "変更しない")]
        for equipment_id, definition in sorted(self._equipment_definitions.items()):
            if definition.slot_type != slot_type:
                continue
            owned = int(self.inventory_state.get("items", {}).get(equipment_id, 0))
            equipped_count = sum(
                1 for unit in self.party_members for eq in unit.equipped.values() if eq == equipment_id
            )
            available = max(0, owned - equipped_count)
            bonus = self._equipment_service.compute_bonuses({slot_type: equipment_id})
            options.append(
                (
                    equipment_id,
                    f"{definition.name} ({equipment_id}) owned={owned} available={available} "
                    f"atk+{bonus['atk']} def+{bonus['defense']} hp+{bonus['hp']} spd+{bonus['spd']}",
                )
            )
        return options

    def equip_item(self, character_id: str, slot_type: str, equipment_id: str) -> list[str]:
        result = self._equipment_service.equip_item(
            party_members=self.party_members,
            inventory_state=self.inventory_state,
            character_id=character_id,
            slot_type=slot_type,
            equipment_id=equipment_id,
        )
        lines = [result.message]
        if result.success:
            lines.extend(self.party_member_lines())
        return lines

    def party_member_lines(self) -> list[str]:
        lines: list[str] = []
        for member in self.party_members:
            final = self._equipment_service.resolve_final_stats(member)
            lines.append(
                f"member:{member.character_id}:lv={member.level}:exp={member.current_exp}/{member.next_level_exp}:"
                f"hp={final['current_hp']}/{final['max_hp']}:sp={final['current_sp']}/{final['max_sp']}:"
                f"atk={final['atk']}:def={final['defense']}:spd={final['spd']}:equipped={member.equipped}"
            )
        return lines

    def usable_item_ids(self) -> list[str]:
        items = self.inventory_state.get("items", {})
        ids: list[str] = []
        for item_id, amount in sorted(items.items()):
            definition = self._item_definitions.get(item_id)
            if definition is None:
                continue
            if definition.get("category") != "consumable":
                continue
            if int(amount) <= 0:
                continue
            ids.append(item_id)
        return ids

    def _run_hunt(self) -> list[str]:
        if self.quest_session is None:
            raise ValueError("ゲームが開始されていません。")
        quest_id = self._active_quest_id()
        if quest_id is None:
            return ["hunt_unavailable:no_active_quest"]
        quest_definition = self.quest_session.quest_service.definitions[quest_id]
        current_location = self._travel_service.location(self.location_state.current_location_id)
        if current_location is None:
            return ["hunt_unavailable:unknown_current_location"]
        if current_location.location_type == "town":
            return ["hunt_unavailable:town_location"]

        target_location_id = self._travel_service.resolve_quest_target_location_id(
            quest_definition.encounter_id,
            quest_definition.target_location_id,
        )
        if target_location_id and target_location_id != self.location_state.current_location_id:
            return [f"hunt_unavailable:wrong_location:required={target_location_id}"]
        encounter_id = current_location.default_encounter_id or quest_definition.encounter_id
        if encounter_id is None:
            return ["hunt_unavailable:no_encounter"]

        battle_party = []
        for member in self.party_members:
            final = self._equipment_service.resolve_final_stats(member)
            battle_party.append(
                PartyMemberState(
                    character_id=member.character_id,
                    level=member.level,
                    current_exp=member.current_exp,
                    next_level_exp=member.next_level_exp,
                    max_hp=final["max_hp"],
                    current_hp=final["current_hp"],
                    max_sp=final["max_sp"],
                    current_sp=final["current_sp"],
                    atk=final["atk"],
                    defense=final["defense"],
                    spd=final["spd"],
                    alive=member.alive,
                    equipped=dict(member.equipped),
                    unlocked_skill_ids=list(member.unlocked_skill_ids),
                )
            )
        try:
            battle_result = self._battle_executor(encounter_id, battle_party)
        except TypeError:
            battle_result = self._battle_executor(encounter_id)
        logs = [f"battle_finished:{encounter_id}:player_won={battle_result.player_won}"]
        if battle_result.player_won:
            battle_reward = self._battle_rewards.get(encounter_id)
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

        self.last_event_id = f"event.system.hunt:{quest_id}"
        self.quest_session.world_flags.add(f"flag.quest.battle_seen:{quest_id}")
        if current_location.can_return_to_hub:
            self.location_state.current_location_id = HUB_LOCATION_ID
            logs.append(f"returned_to_hub:{HUB_LOCATION_ID}")
        return logs

    def _build_session(self) -> QuestSliceSession:
        return QuestSliceSession(
            quest_service=QuestProgressService(self._quest_board_service.definitions),
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
            f"location:{self.location_state.current_location_id}",
            f"party_members:{len(self.party_members)}",
            f"last_event_id:{self.last_event_id}",
            f"gold:{self.inventory_state.get('gold', 0)}",
            f"world_flags:{sorted(self.quest_session.world_flags)}",
        ]
        lines.extend(self.party_member_lines())
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

    def _usable_item_lines(self) -> list[str]:
        item_ids = self.usable_item_ids()
        if not item_ids:
            return ["usable_item:none"]

        lines: list[str] = []
        items = self.inventory_state.get("items", {})
        for item_id in item_ids:
            definition = self._item_definitions[item_id]
            lines.append(
                f"usable_item:{item_id}:{definition.get('name', item_id)}:stock={items.get(item_id, 0)}:"
                f"effect={definition.get('effect_type')}:{definition.get('effect_value')}"
            )
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

    def _party_level(self) -> int:
        if not self.party_members:
            return 1
        return max(member.level for member in self.party_members)

    def _active_quest_id(self) -> str | None:
        if self.quest_session is None:
            return None
        for quest_id, state in sorted(self.quest_session.quest_states.items()):
            if state.status == QuestStatus.IN_PROGRESS:
                return quest_id
        return None

    def _ready_to_complete_quest_id(self) -> str | None:
        if self.quest_session is None:
            return None
        for quest_id, state in sorted(self.quest_session.quest_states.items()):
            if state.status == QuestStatus.READY_TO_COMPLETE:
                return quest_id
        return None

    def _has_active_quest(self) -> bool:
        return self._active_quest_id() is not None

    def _location_can_hunt(self) -> bool:
        current = self._travel_service.location(self.location_state.current_location_id)
        if current is None:
            return False
        return current.location_type != "town"

    def _has_reportable_quest(self) -> bool:
        return self._ready_to_complete_quest_id() is not None

    def quest_state(self, quest_id: str = "quest.ch01.missing_port_record") -> QuestState | None:
        if self.quest_session is None:
            return None
        return self.quest_session.quest_states.get(quest_id)
