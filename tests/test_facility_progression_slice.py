from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.app.application.facility_progression_service import FacilityProgressContext, FacilityProgressService
from game.app.infrastructure.facility_master_data_repository import FacilityMasterDataRepository
from game.quest.domain.entities import BattleResult, QuestStatus


class FacilityProgressionSliceTests(unittest.TestCase):
    def _build_app(self, tmp_dir: str) -> PlayableSliceApplication:
        def battle_executor(encounter_id: str) -> BattleResult:
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

    def test_load_hub_facility_definitions(self) -> None:
        repo = FacilityMasterDataRepository(Path("data/master"))
        facilities = repo.load_facilities()

        self.assertIn("facility.hub.workshop", facilities)
        self.assertIn("facility.hub.general_store", facilities)
        self.assertEqual(facilities["facility.hub.workshop"].levels[1].requirements.required_turn_in_count, 1)
        self.assertIn("equip.weapon.prayer_staff", facilities["facility.hub.general_store"].levels[1].unlocks.shop_stock_ids)

    def test_progress_service_prevents_duplicate_level_up(self) -> None:
        repo = FacilityMasterDataRepository(Path("data/master"))
        facilities = repo.load_facilities()
        service = FacilityProgressService()
        levels = {"facility.hub.workshop": 1}

        first = service.evaluate_level_up(
            definitions={"facility.hub.workshop": facilities["facility.hub.workshop"]},
            facility_levels=levels,
            context=FacilityProgressContext(
                completed_quest_ids={"quest.ch01.workshop_supply_chain"},
                world_flags={"flag.hub.facility.workshop.level1"},
                turn_in_count=1,
            ),
        )
        self.assertEqual(len(first), 1)
        self.assertEqual(levels["facility.hub.workshop"], 2)

        second = service.evaluate_level_up(
            definitions={"facility.hub.workshop": facilities["facility.hub.workshop"]},
            facility_levels=levels,
            context=FacilityProgressContext(
                completed_quest_ids={"quest.ch01.workshop_supply_chain"},
                world_flags={"flag.hub.facility.workshop.level1"},
                turn_in_count=99,
            ),
        )
        self.assertEqual(second, [])

    def test_facility_unlocks_recipe_shop_dialogue_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            self.assertEqual(app.facility_levels["facility.hub.workshop"], 1)
            self.assertEqual(app.facility_levels["facility.hub.general_store"], 1)
            self.assertIn("flag.hub.facility.workshop.level1", app.quest_session.world_flags)

            locked_buy = app.buy_item("equip.weapon.prayer_staff")
            self.assertEqual(locked_buy, ["purchase_failed:shop_stock_locked:shop.astel.general_store:equip.weapon.prayer_staff"])

            app._apply_recipe_discovery("dialogue_event", "dialogue.workshop.rank2_blueprint")
            app.inventory_state["items"]["item.material.iron_fragment"] = 10
            app.inventory_state["items"]["item.consumable.antidote_leaf"] = 10
            self.assertEqual(
                app.craft_recipe("recipe.craft.tidal_guard_talisman"),
                ["craft_failed:required_workshop_rank:recipe=recipe.craft.tidal_guard_talisman"],
            )

            app.accept_quest("quest.ch01.workshop_supply_chain")
            app.quest_session.quest_states["quest.ch01.workshop_supply_chain"].status = QuestStatus.READY_TO_COMPLETE
            workshop_report_logs = app.perform_action("report")
            self.assertTrue(any(line.startswith("facility_level_up:facility.hub.workshop:level=1->2") for line in workshop_report_logs))

            app.quest_session.quest_states["quest.ch01.memory_fragment_delivery"] = (
                app.quest_session.quest_service.create_initial_state("quest.ch01.memory_fragment_delivery")
            )
            app.quest_session.quest_states["quest.ch01.memory_fragment_delivery"].status = QuestStatus.READY_TO_COMPLETE
            shop_report_logs = app.perform_action("report")
            self.assertTrue(any(line.startswith("facility_level_up:facility.hub.general_store:level=1->2") for line in shop_report_logs))
            self.assertIn("flag.hub.facility.workshop.level2", app.quest_session.world_flags)

            workshop_dialogue = app.talk_to_npc("npc.astel.workshop_master", choice_selector=lambda *_: "choice.rank2_learn")
            self.assertTrue(any("dialogue.workshop.rank2_blueprint" in line for line in workshop_dialogue))
            self.assertTrue(any("recipe.craft.tidal_guard_talisman" in line for line in workshop_dialogue))

            buy_logs = app.buy_item("equip.weapon.prayer_staff")
            self.assertTrue(buy_logs[0].startswith("purchase_succeeded:shop.astel.general_store:equip.weapon.prayer_staff"))
            crafted = app.craft_recipe("recipe.craft.tidal_guard_talisman")
            self.assertIn("crafted:recipe.craft.tidal_guard_talisman", crafted)

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            self.assertEqual(resumed.facility_levels["facility.hub.workshop"], 2)
            self.assertEqual(resumed.facility_levels["facility.hub.general_store"], 2)
            self.assertIn("recipe.craft.tidal_guard_talisman", resumed.facility_unlocked_recipe_ids)
            self.assertIn("equip.weapon.prayer_staff", resumed.facility_unlocked_shop_stock_ids)


if __name__ == "__main__":
    unittest.main()
