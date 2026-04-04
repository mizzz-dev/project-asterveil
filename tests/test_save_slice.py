from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from game.quest.application.session import QuestSliceSession
from game.quest.cli.run_quest_slice import build_battle_executor
from game.quest.domain.entities import QuestStatus
from game.quest.domain.services import QuestProgressService
from game.quest.infrastructure.master_data_repository import QuestMasterDataRepository
from game.save.application.session import SaveSliceApplicationService
from game.save.domain.entities import PartyMemberState, SaveData
from game.save.infrastructure.repository import InMemorySaveRepository, JsonFileSaveRepository


class SaveSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.master_root = Path("data/master")
        self.quest_repo = QuestMasterDataRepository(self.master_root)
        self.app_service = SaveSliceApplicationService()

    def _build_session(self) -> QuestSliceSession:
        return QuestSliceSession(
            quest_service=QuestProgressService(self.quest_repo.load_quests()),
            events=self.quest_repo.load_events(),
            battle_executor=build_battle_executor(self.master_root),
        )

    def _party_sample(self) -> list[PartyMemberState]:
        return [
            PartyMemberState(
                character_id="char.main.rion",
                level=8,
                current_hp=111,
                current_sp=76,
                alive=True,
                equipped={"weapon": "equip.weapon.bronze_blade"},
                unlocked_skill_ids=["skill.striker.flare_slash"],
            )
        ]

    def test_save_and_restore_with_file_repository(self) -> None:
        session = self._build_session()
        session.play_event("event.ch01.port_request")

        save_data = self.app_service.build_save_data(
            quest_session=session,
            party_members=self._party_sample(),
            last_event_id="event.ch01.port_request",
            play_time_sec=88,
            inventory_state={"gold": 320},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = JsonFileSaveRepository(Path(tmp_dir) / "slot_01.json")
            repo.save(save_data)

            loaded = repo.load()

        resumed = self._build_session()
        last_event_id = self.app_service.restore_quest_session(resumed, loaded)

        quest_state = resumed.quest_states["quest.ch01.missing_port_record"]
        self.assertEqual(last_event_id, "event.ch01.port_request")
        self.assertEqual(quest_state.status, QuestStatus.READY_TO_COMPLETE)
        self.assertIn("flag.ch01.port_wraith_battle_seen", resumed.world_flags)
        self.assertEqual(loaded.party_members[0].current_hp, 111)

        resumed.play_event("event.ch01.port_report")
        self.assertEqual(quest_state.status, QuestStatus.COMPLETED)

    def test_inmemory_repository_roundtrip(self) -> None:
        session = self._build_session()
        session.play_event("event.ch01.port_request")

        repo = InMemorySaveRepository()
        repo.save(
            self.app_service.build_save_data(
                quest_session=session,
                party_members=self._party_sample(),
                last_event_id="event.ch01.port_request",
            )
        )

        loaded = repo.load()
        self.assertEqual(loaded.save_version, 1)
        self.assertEqual(loaded.party_members[0].character_id, "char.main.rion")

    def test_broken_data_detection(self) -> None:
        broken = {
            "save_version": 1,
            "player_profile": {"difficulty": "standard", "play_time_sec": 0},
            "party_state": {"members": []},
            "quest_state": {},
            "world_flags": {},
        }

        with self.assertRaises(ValueError):
            SaveData.from_dict(broken)

    def test_missing_required_top_level_field_detection(self) -> None:
        broken = {
            "save_version": 1,
            "player_profile": {
                "difficulty": "standard",
                "play_time_sec": 0,
                "last_saved_at": "2026-04-04T00:00:00Z",
            },
            "party_state": {"members": []},
            "world_flags": {},
        }
        with self.assertRaises(ValueError):
            SaveData.from_dict(broken)


if __name__ == "__main__":
    unittest.main()
