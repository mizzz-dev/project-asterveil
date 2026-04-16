from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.location.domain.field_event_service import FieldEventService
from game.location.infrastructure.field_event_repository import FieldEventMasterDataRepository
from game.quest.domain.entities import BattleResult


class FieldBranchEventSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FieldEventMasterDataRepository(Path("data/master"))

    def _build_app(self, tmp_dir: str, *, encounters: list[str]) -> PlayableSliceApplication:
        def battle_executor(encounter_id: str, *_args, **_kwargs) -> BattleResult:
            encounters.append(encounter_id)
            return BattleResult(
                encounter_id=encounter_id,
                player_won=True,
                defeated_enemy_ids=("enemy.ch01.port_wraith",),
            )

        return PlayableSliceApplication(
            master_root=Path("data/master"),
            save_file_path=Path(tmp_dir) / "slot_01.json",
            battle_executor=battle_executor,
        )

    def test_load_branching_field_event_definitions(self) -> None:
        definitions = self.repository.load_events()
        self.assertIn("event.field.tidal_flats.drift_supply", definitions)
        self.assertIn("event.field.tidal_flats.toxic_mushroom", definitions)
        drift = definitions["event.field.tidal_flats.drift_supply"]
        self.assertEqual(drift.trigger_type, "manual_explore")
        self.assertEqual(len(drift.choices), 2)
        self.assertTrue(any(outcome.outcome_type == "start_battle" for outcome in drift.choices[1].outcomes))

    def test_list_by_location_and_repeatable_policy(self) -> None:
        definitions = self.repository.load_events()
        service = FieldEventService(definitions)
        statuses = service.list_events_for_location(
            location_id="location.field.tidal_flats",
            world_flags=set(),
            completed_event_ids={"event.field.tidal_flats.drift_supply"},
        )
        drift = next(status for status in statuses if status.event_id == "event.field.tidal_flats.drift_supply")
        toxic = next(status for status in statuses if status.event_id == "event.field.tidal_flats.toxic_mushroom")
        self.assertFalse(drift.can_execute)
        self.assertEqual(drift.reason_code, "already_completed")
        self.assertTrue(toxic.repeatable)

    def test_choice_branching_battle_items_flags_and_status_effect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            encounters: list[str] = []
            app = self._build_app(tmp_dir, encounters=encounters)
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            app.travel_to("location.field.tidal_flats")

            risky_logs = app.resolve_field_event_choice(
                "event.field.tidal_flats.drift_supply",
                "choice.risky_open",
            )
            self.assertIn("field_event_resolved:event.field.tidal_flats.drift_supply", risky_logs)
            self.assertIn("field_choice_selected:event.field.tidal_flats.drift_supply:choice.risky_open", risky_logs)
            self.assertIn("encounter.ch01.port_wraith", encounters)
            self.assertIn("flag.field_event.tidal_flats.risky_supply_opened", app.quest_session.world_flags)
            self.assertGreaterEqual(app.inventory_state["items"].get("item.material.memory_shard", 0), 1)
            self.assertIn("event.field.tidal_flats.drift_supply", app.completed_field_event_ids)

            already = app.resolve_field_event_choice(
                "event.field.tidal_flats.drift_supply",
                "choice.safe_collect",
            )
            self.assertEqual(already, ["field_event_already_completed:event.field.tidal_flats.drift_supply"])

            harvest_logs = app.resolve_field_event_choice(
                "event.field.tidal_flats.toxic_mushroom",
                "choice.harvest_patch",
            )
            self.assertIn("field_event_effect_applied:effect.ailment.poison:turns=2:targets=1", harvest_logs)
            self.assertIn("flag.field_event.tidal_flats.hidden_cache_unlocked", app.quest_session.world_flags)
            self.assertTrue(
                any(effect.effect_id == "effect.ailment.poison" for effect in app.party_members[0].active_effects)
            )
            app.travel_to("location.town.astel")
            guard_logs = app.talk_to_npc("npc.astel.guard")
            self.assertTrue(any("隠し包み" in line for line in guard_logs))
            app.travel_to("location.field.tidal_flats")

            repeat_logs = app.resolve_field_event_choice(
                "event.field.tidal_flats.toxic_mushroom",
                "choice.avoid_patch",
            )
            self.assertIn("field_choice_selected:event.field.tidal_flats.toxic_mushroom:choice.avoid_patch", repeat_logs)

    def test_save_load_keeps_completed_and_choice_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            encounters: list[str] = []
            app = self._build_app(tmp_dir, encounters=encounters)
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            app.travel_to("location.field.tidal_flats")
            app.resolve_field_event_choice("event.field.tidal_flats.drift_supply", "choice.safe_collect")
            app.resolve_field_event_choice("event.field.tidal_flats.toxic_mushroom", "choice.harvest_patch")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir, encounters=[])
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            self.assertIn("event.field.tidal_flats.drift_supply", resumed.completed_field_event_ids)
            self.assertEqual(
                resumed.field_event_choice_history["event.field.tidal_flats.drift_supply"],
                "choice.safe_collect",
            )
            self.assertEqual(
                resumed.field_event_choice_history["event.field.tidal_flats.toxic_mushroom"],
                "choice.harvest_patch",
            )


if __name__ == "__main__":
    unittest.main()
