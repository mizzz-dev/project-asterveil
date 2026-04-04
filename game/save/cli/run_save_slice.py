from __future__ import annotations

from pathlib import Path

from game.quest.application.session import QuestSliceSession
from game.quest.cli.run_quest_slice import build_battle_executor
from game.quest.domain.services import QuestProgressService
from game.quest.infrastructure.master_data_repository import QuestMasterDataRepository
from game.save.application.session import SaveSliceApplicationService
from game.save.domain.entities import PartyMemberState
from game.save.infrastructure.repository import JsonFileSaveRepository


def run_save_vertical_slice() -> int:
    master_root = Path("data/master")
    save_path = Path("tmp/save_slot_01.json")
    quest_repo = QuestMasterDataRepository(master_root)

    quest_session = QuestSliceSession(
        quest_service=QuestProgressService(quest_repo.load_quests()),
        events=quest_repo.load_events(),
        battle_executor=build_battle_executor(master_root),
    )

    print("[Flow] 受注と戦闘を進行")
    request_logs = quest_session.play_event("event.ch01.port_request")
    for line in request_logs:
        print(f"- {line}")

    app_service = SaveSliceApplicationService()
    party = [
        PartyMemberState(
            character_id="char.main.rion",
            level=8,
            current_hp=108,
            current_sp=88,
            alive=True,
            equipped={"weapon": "equip.weapon.bronze_blade"},
            unlocked_skill_ids=["skill.striker.flare_slash"],
        )
    ]

    save_data = app_service.build_save_data(
        quest_session=quest_session,
        party_members=party,
        last_event_id="event.ch01.port_request",
        play_time_sec=120,
        inventory_state={"gold": 320, "items": {"item.material.memory_shard": 3}},
        meta={"save_slot": "slot_01"},
    )
    save_repo = JsonFileSaveRepository(save_path)
    save_repo.save(save_data)
    print(f"[Flow] セーブ完了: {save_path}")

    reloaded = save_repo.load()

    resumed_session = QuestSliceSession(
        quest_service=QuestProgressService(quest_repo.load_quests()),
        events=quest_repo.load_events(),
        battle_executor=build_battle_executor(master_root),
    )
    last_event_id = app_service.restore_quest_session(resumed_session, reloaded)
    print(f"[Flow] ロード完了: last_event_id={last_event_id}")

    report_logs = resumed_session.play_event("event.ch01.port_report")
    for line in report_logs:
        print(f"- {line}")

    save_repo.save(
        app_service.build_save_data(
            quest_session=resumed_session,
            party_members=reloaded.party_members,
            last_event_id="event.ch01.port_report",
            play_time_sec=reloaded.player_profile.play_time_sec + 60,
            inventory_state=reloaded.inventory_state,
            meta=reloaded.meta,
        )
    )
    print("[Flow] 再セーブ完了")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_save_vertical_slice())
