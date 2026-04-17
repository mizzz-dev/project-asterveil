from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.equipment_service import EquipmentService
from game.app.application.equipment_set_service import EquipmentSetService
from game.app.application.playable_slice import PlayableSliceApplication
from game.app.infrastructure.master_data_repository import AppMasterDataRepository
from game.crafting.infrastructure.master_data_repository import CraftingMasterDataRepository
from game.quest.domain.entities import BattleResult
from game.save.domain.entities import PartyMemberState


class EquipmentSetBonusSliceTests(unittest.TestCase):
    def test_set_definition_loaded_with_two_and_three_piece_bonuses(self) -> None:
        repo = AppMasterDataRepository(Path("data/master"))
        equipment = repo.load_equipment()
        sets = repo.load_equipment_sets(set(equipment))

        self.assertIn("set.tidebreaker.assault", sets)
        definition = sets["set.tidebreaker.assault"]
        self.assertIn("equip.armor.tidebreaker_harness", definition.member_equipment_ids)
        self.assertIn("equip.weapon.memory_edge", definition.member_equipment_ids)
        self.assertIn("equip.accessory.tidecrest_ring", definition.member_equipment_ids)
        self.assertIn(2, {bonus.required_piece_count for bonus in definition.set_bonuses})
        self.assertIn(3, {bonus.required_piece_count for bonus in definition.set_bonuses})

    def test_set_bonus_applies_stat_and_passive_and_deactivates(self) -> None:
        repo = AppMasterDataRepository(Path("data/master"))
        equipment = repo.load_equipment()
        set_service = EquipmentSetService(repo.load_equipment_sets(set(equipment)))
        service = EquipmentService(
            equipment,
            set_stat_bonus_resolver=lambda equipped: set_service.compute_stat_bonus(equipped),
            set_passive_resolver=lambda equipped: tuple(),
        )

        two_piece_member = PartyMemberState(
            character_id="char.main.rion",
            level=8,
            max_hp=120,
            current_hp=120,
            max_sp=100,
            current_sp=100,
            atk=24,
            defense=16,
            spd=18,
            equipped={
                "weapon": "equip.weapon.memory_edge",
                "armor": "equip.armor.tidebreaker_harness",
            },
        )
        two_piece = service.resolve_final_stats(two_piece_member)
        self.assertEqual(two_piece["atk"], 37)
        self.assertEqual(two_piece["defense"], 23)
        self.assertEqual(two_piece["spd"], 19)

        three_piece_member = PartyMemberState(
            character_id="char.main.rion",
            level=8,
            max_hp=120,
            current_hp=120,
            max_sp=100,
            current_sp=100,
            atk=24,
            defense=16,
            spd=18,
            equipped={
                "weapon": "equip.weapon.memory_edge",
                "armor": "equip.armor.tidebreaker_harness",
                "accessory": "equip.accessory.tidecrest_ring",
            },
        )
        three_piece = service.resolve_final_stats(three_piece_member)
        self.assertEqual(three_piece["atk"], 41)
        self.assertEqual(three_piece["defense"], 24)
        self.assertEqual(three_piece["spd"], 20)

        deactivated_member = PartyMemberState(
            character_id="char.main.rion",
            level=8,
            max_hp=120,
            current_hp=120,
            max_sp=100,
            current_sp=100,
            atk=24,
            defense=16,
            spd=18,
            equipped={
                "weapon": "equip.weapon.bronze_blade",
                "armor": "equip.armor.tidebreaker_harness",
                "accessory": "equip.accessory.tidecrest_ring",
            },
        )
        deactivated = service.resolve_final_stats(deactivated_member)
        self.assertEqual(deactivated["atk"], 33)
        self.assertEqual(deactivated["spd"], 18)

    def test_playable_slice_equip_transition_battle_and_save_load(self) -> None:
        captured: dict[str, int] = {}

        def battle_executor(encounter_id: str, party_members=None) -> BattleResult:
            self.assertEqual(encounter_id, "encounter.ch01.port_wraith")
            if party_members:
                captured["atk"] = party_members[0].atk
                captured["defense"] = party_members[0].defense
                captured["spd"] = party_members[0].spd
            return BattleResult(encounter_id=encounter_id, player_won=False, defeated_enemy_ids=tuple())

        with tempfile.TemporaryDirectory() as tmp_dir:
            app = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")

            app.inventory_state["items"]["equip.weapon.memory_edge"] = 1
            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.inventory_state["items"]["equip.accessory.tidecrest_ring"] = 1

            self.assertIn("workshop_set_bonus_hint:set.tidebreaker.assault:未成立", app.workshop_set_bonus_guidance_lines())

            logs_1 = app.equip_item("char.main.rion", "weapon", "equip.weapon.memory_edge")
            self.assertFalse(any(line.startswith("set_bonus_activated:") for line in logs_1))

            logs_2 = app.equip_item("char.main.rion", "armor", "equip.armor.tidebreaker_harness")
            self.assertTrue(any("set_bonus_activated:char.main.rion:set.tidebreaker.assault:2:stat_bonus" in line for line in logs_2))
            self.assertIn("workshop_set_bonus_hint:set.tidebreaker.assault:2/3部位達成", app.workshop_set_bonus_guidance_lines())

            logs_3 = app.equip_item("char.main.rion", "accessory", "equip.accessory.tidecrest_ring")
            self.assertTrue(any("set_bonus_activated:char.main.rion:set.tidebreaker.assault:3:stat_bonus" in line for line in logs_3))
            self.assertTrue(any("set_bonus_activated:char.main.rion:set.tidebreaker.assault:3:status_resistance" in line for line in logs_3))
            self.assertIn("workshop_set_bonus_hint:set.tidebreaker.assault:全段階発動中", app.workshop_set_bonus_guidance_lines())

            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            self.assertEqual(captured["atk"], 41)
            self.assertEqual(captured["defense"], 24)
            self.assertEqual(captured["spd"], 20)

            app.perform_action("save")
            resumed = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            status_lines = resumed.perform_action("status")
            self.assertTrue(any("active_set_bonuses=['[2部位発動]潮断共鳴セット:stat_bonus:2部位で攻防が上昇する。" in line for line in status_lines))

            remove_logs = resumed.equip_item("char.main.rion", "weapon", "equip.weapon.bronze_blade")
            self.assertTrue(any("set_bonus_deactivated:char.main.rion:set.tidebreaker.assault:3:stat_bonus" in line for line in remove_logs))
            self.assertTrue(any("set_bonus_deactivated:char.main.rion:set.tidebreaker.assault:3:status_resistance" in line for line in remove_logs))

    def test_set_bonus_keeps_active_with_upgraded_equipment_and_after_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
            )
            app.new_game()

            app.inventory_state["items"]["equip.weapon.memory_edge"] = 1
            app.inventory_state["items"]["equip.armor.tidebreaker_harness"] = 1
            app.inventory_state["items"]["equip.accessory.tidecrest_ring"] = 1
            app.inventory_state["items"]["item.material.relic.deepsea_thread"] = 3
            app.inventory_state["items"]["item.material.iron_fragment"] = 5
            app.inventory_state["items"]["item.material.guardian_core"] = 5
            app.workshop_progress_state.level = 4

            app.equip_item("char.main.rion", "weapon", "equip.weapon.memory_edge")
            app.equip_item("char.main.rion", "armor", "equip.armor.tidebreaker_harness")
            app.equip_item("char.main.rion", "accessory", "equip.accessory.tidecrest_ring")
            before_upgrade = app.perform_action("status")
            self.assertTrue(any("[3部位発動]潮断共鳴セット:status_resistance:3部位で毒耐性を得る。" in line for line in before_upgrade))

            upgrade_logs = app.upgrade_equipment("equip.armor.tidebreaker_harness")
            self.assertIn("equipment_upgrade_success:equip.armor.tidebreaker_harness:upgrade_level:+1:current=1", upgrade_logs)
            after_upgrade = app.perform_action("status")
            self.assertTrue(any("upgrade_level:equip.armor.tidebreaker_harness:lv1" in line for line in after_upgrade))
            self.assertTrue(any("[3部位発動]潮断共鳴セット:stat_bonus:3部位でさらに攻撃と速度が上昇する。" in line for line in after_upgrade))

            app.perform_action("save")
            resumed = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
            )
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            resumed_status = resumed.perform_action("status")
            self.assertTrue(any("upgrade_level:equip.armor.tidebreaker_harness:lv1" in line for line in resumed_status))
            self.assertTrue(any("[3部位発動]潮断共鳴セット:status_resistance:3部位で毒耐性を得る。" in line for line in resumed_status))

    def test_set_equipment_connected_to_advanced_crafting_and_miniboss_material(self) -> None:
        repo = CraftingMasterDataRepository(Path("data/master"))
        app_repo = AppMasterDataRepository(Path("data/master"))
        recipes = repo.load_recipes(valid_item_ids=set(app_repo.load_items()), valid_equipment_ids=set(app_repo.load_equipment()))

        harness = recipes["recipe.craft.tidebreaker_harness"]
        ring = recipes["recipe.craft.tidecrest_ring"]
        harness_ingredient_ids = {ingredient.item_id for ingredient in harness.ingredients}

        self.assertIn("item.material.miniboss.guardian_core", harness_ingredient_ids)
        self.assertEqual(harness.required_workshop_level, 3)
        self.assertEqual(ring.required_workshop_level, 3)


if __name__ == "__main__":
    unittest.main()
