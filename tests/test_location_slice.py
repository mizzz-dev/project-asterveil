from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import HUB_LOCATION_ID, PlayableSliceApplication
from game.location.application.travel_service import TravelService
from game.location.domain.entities import LocationState
from game.location.infrastructure.master_data_repository import LocationMasterDataRepository
from game.quest.domain.entities import BattleResult, QuestStatus


class LocationSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = LocationMasterDataRepository(Path("data/master"))
        self.locations = self.repo.load_locations()
        self.travel_service = TravelService(self.locations, hub_location_id=HUB_LOCATION_ID)

    def test_load_location_master_data(self) -> None:
        self.assertIn(HUB_LOCATION_ID, self.locations)
        self.assertIn("location.field.tidal_flats", self.locations)
        self.assertEqual(self.locations["location.field.tidal_flats"].default_encounter_id, "encounter.ch01.port_wraith")

    def test_travel_success_and_failures(self) -> None:
        state = LocationState(
            current_location_id=HUB_LOCATION_ID,
            unlocked_location_ids={HUB_LOCATION_ID, "location.field.tidal_flats"},
        )
        result = self.travel_service.travel_to(state, "location.field.tidal_flats")
        self.assertTrue(result.success)
        self.assertEqual(state.current_location_id, "location.field.tidal_flats")

        locked = self.travel_service.travel_to(state, "location.dungeon.sunken_storehouse")
        self.assertEqual(locked.code, "locked")

        invalid = self.travel_service.travel_to(state, "location.unknown")
        self.assertEqual(invalid.code, "invalid_location")

    def test_playable_location_hunt_and_save_load(self) -> None:
        def battle_executor(encounter_id: str, *_args, **_kwargs) -> BattleResult:
            self.assertEqual(encounter_id, "encounter.ch01.port_wraith")
            return BattleResult(
                encounter_id=encounter_id,
                player_won=True,
                defeated_enemy_ids=("enemy.ch01.port_wraith",),
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            app = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")

            travel_logs = app.travel_to("location.field.tidal_flats")
            self.assertIn("travel_succeeded:location.field.tidal_flats", travel_logs)
            if "location_event_started:event.location.tidal_flats.first_entry" in travel_logs:
                self.assertIn("quest_status_changed:quest.ch01.missing_port_record:ready_to_complete", travel_logs)
            else:
                hunt_logs = app.perform_action("hunt")
                self.assertIn("quest_status_changed:quest.ch01.missing_port_record:ready_to_complete", hunt_logs)
                self.assertIn("returned_to_hub:location.town.astel", hunt_logs)
            self.assertEqual(app.quest_state("quest.ch01.missing_port_record").status, QuestStatus.READY_TO_COMPLETE)

            app.perform_action("save")
            resumed = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            if "location_event_started:event.location.tidal_flats.first_entry" in travel_logs:
                self.assertEqual(resumed.location_state.current_location_id, "location.field.tidal_flats")
            else:
                self.assertEqual(resumed.location_state.current_location_id, HUB_LOCATION_ID)
            self.assertIn("location.field.tidal_flats", resumed.location_state.unlocked_location_ids)


if __name__ == "__main__":
    unittest.main()
