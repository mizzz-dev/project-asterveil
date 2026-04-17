from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.location.domain.miniboss_service import MinibossService
from game.location.infrastructure.miniboss_repository import MinibossMasterDataRepository
from game.quest.domain.entities import BattleResult


class FieldMinibossSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = MinibossMasterDataRepository(Path("data/master"))
        self.valid_encounter_ids = {
            "encounter.ch01.port_wraith_single",
            "encounter.ch01.port_wraith",
            "encounter.ch01.harbor_miasma_patrol",
            "encounter.ch01.tide_serpent_boss",
        }

    def _build_app(self, tmp_dir: str, encounters: list[str]) -> PlayableSliceApplication:
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

    def test_load_miniboss_definition(self) -> None:
        definitions = self.repo.load_definitions(
            valid_item_ids={
                "item.key.recipe_book.tidal_tonic_notes",
                "item.material.memory_shard",
                "item.material.miniboss.guardian_core",
            },
            valid_encounter_ids=self.valid_encounter_ids,
        )
        self.assertIn("miniboss.ch01.tidal_flats.shrine_guardian", definitions)
        definition = definitions["miniboss.ch01.tidal_flats.shrine_guardian"]
        self.assertEqual(definition.trigger_event_id, "event.field.tidal_flats.sunken_shrine_switch")
        self.assertFalse(definition.repeatable)

    def test_miniboss_service_detects_trigger_mismatch(self) -> None:
        definitions = self.repo.load_definitions(
            valid_item_ids={
                "item.key.recipe_book.tidal_tonic_notes",
                "item.material.memory_shard",
                "item.material.miniboss.guardian_core",
            },
            valid_encounter_ids=self.valid_encounter_ids,
        )
        service = MinibossService(definitions)
        result = service.resolve_start(
            miniboss_id="miniboss.ch01.tidal_flats.shrine_guardian",
            trigger_event_id="event.field.tidal_flats.drift_supply",
            location_id="location.field.tidal_flats",
            defeated_miniboss_ids=set(),
        )
        self.assertFalse(result.success)
        self.assertIn("trigger_mismatch", result.code)

    def test_field_event_miniboss_first_clear_reward_and_no_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            encounters: list[str] = []
            app = self._build_app(tmp_dir, encounters)
            app.new_game()
            app.travel_to("location.field.tidal_flats")

            before_logs = app.field_event_lines()
            self.assertTrue(any("field_event_miniboss:event.field.tidal_flats.sunken_shrine_switch" in line for line in before_logs))
            self.assertTrue(any("[未撃破]" in line for line in before_logs))

            safe_logs = app.resolve_field_event_choice(
                "event.field.tidal_flats.sunken_shrine_switch",
                "choice.leave_it",
            )
            self.assertIn("field_event_item_granted:item.consumable.antidote_leaf:x1", safe_logs)
            app.travel_to("location.town.astel")
            hint_lines = app.talk_to_npc("npc.astel.guard")
            self.assertTrue(any("封印がきしむ音" in line for line in hint_lines))
            app.travel_to("location.field.tidal_flats")

            risky_logs = app.resolve_field_event_choice(
                "event.field.tidal_flats.sunken_shrine_switch",
                "choice.pull_lever",
            )
            self.assertIn("encounter.ch01.harbor_miasma_patrol", encounters)
            self.assertTrue(any(line.startswith("miniboss_encounter_started:miniboss.ch01.tidal_flats.shrine_guardian") for line in risky_logs))
            self.assertIn(
                "miniboss_first_clear_reward:miniboss.ch01.tidal_flats.shrine_guardian:item.key.recipe_book.tidal_tonic_notes:x1",
                risky_logs,
            )
            self.assertIn(
                "miniboss_first_clear_reward:miniboss.ch01.tidal_flats.shrine_guardian:item.material.miniboss.guardian_core:x1",
                risky_logs,
            )
            self.assertTrue(any(line.startswith("recipe_discovered:recipe.craft.tidal_tonic") for line in risky_logs))
            self.assertIn("flag.miniboss.tidal_flats.guardian_defeated", app.quest_session.world_flags)

            app.travel_to("location.town.astel")
            after_lines = app.talk_to_npc("npc.astel.guard")
            self.assertTrue(any("潮祠の守り手を倒した" in line for line in after_lines))
            app.travel_to("location.field.tidal_flats")

            retry_logs = app.resolve_field_event_choice(
                "event.field.tidal_flats.sunken_shrine_switch",
                "choice.pull_lever",
            )
            self.assertEqual(retry_logs, ["field_event_failed:condition_not_met:event.field.tidal_flats.sunken_shrine_switch"])

    def test_save_load_keeps_miniboss_defeat_and_reward_claim_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir, [])
            app.new_game()
            app.travel_to("location.field.tidal_flats")
            app.resolve_field_event_choice("event.field.tidal_flats.sunken_shrine_switch", "choice.pull_lever")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir, [])
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            self.assertIn("miniboss.ch01.tidal_flats.shrine_guardian", resumed.defeated_miniboss_ids)
            self.assertIn(
                "miniboss.ch01.tidal_flats.shrine_guardian",
                resumed.miniboss_first_clear_reward_claimed_ids,
            )


if __name__ == "__main__":
    unittest.main()
