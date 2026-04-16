from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.battle.application.equipment_passive_service import EquipmentPassiveService, PassiveEffect
from game.quest.domain.entities import BattleResult, QuestStatus


class EquipmentPassiveSliceTests(unittest.TestCase):
    def test_invalid_passive_definition_is_detected(self) -> None:
        service = EquipmentPassiveService(
            {
                "equip.test.invalid": (
                    PassiveEffect(
                        passive_id="passive.test.invalid",
                        passive_type="unknown_type",
                        target="self",
                        parameters={},
                    ),
                )
            }
        )
        with self.assertRaisesRegex(ValueError, "unsupported passive_type"):
            service.resolve_context({"weapon": "equip.test.invalid"})

    def test_shop_to_equip_to_save_load_keeps_passive_summary(self) -> None:
        captured: dict[str, dict[str, str]] = {}

        def battle_executor(encounter_id: str, party_members=None) -> BattleResult:
            self.assertEqual(encounter_id, "encounter.ch01.port_wraith")
            if party_members:
                captured["equipped"] = dict(party_members[0].equipped)
            return BattleResult(encounter_id=encounter_id, player_won=False, defeated_enemy_ids=tuple())

        with tempfile.TemporaryDirectory() as tmp_dir:
            app = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            app.quest_session.quest_states["quest.ch01.memory_fragment_delivery"] = (
                app.quest_session.quest_service.create_initial_state("quest.ch01.memory_fragment_delivery")
            )
            app.quest_session.quest_states["quest.ch01.memory_fragment_delivery"].status = QuestStatus.READY_TO_COMPLETE
            app.perform_action("report")

            app.buy_item("equip.weapon.prayer_staff")
            equip_logs = app.equip_item("char.main.rion", "weapon", "equip.weapon.prayer_staff")
            self.assertIn("equip_succeeded:char.main.rion:weapon:equip.weapon.prayer_staff", equip_logs)
            self.assertTrue(any("heal_bonus" in line for line in equip_logs))

            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            self.assertEqual(captured["equipped"]["weapon"], "equip.weapon.prayer_staff")

            app.perform_action("save")
            resumed = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            resumed.continue_game()
            status_logs = resumed.perform_action("status")
            self.assertTrue(any("equip.weapon.prayer_staff" in line for line in status_logs))
            self.assertTrue(any("heal_bonus" in line for line in status_logs))


if __name__ == "__main__":
    unittest.main()
