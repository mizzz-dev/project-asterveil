from __future__ import annotations

import unittest
from pathlib import Path

from game.app.application.equipment_service import EquipmentService
from game.app.infrastructure.master_data_repository import AppMasterDataRepository
from game.save.domain.entities import PartyMemberState


class EquipmentSliceTests(unittest.TestCase):
    def test_load_equipment_definitions(self) -> None:
        repo = AppMasterDataRepository(Path("data/master"))
        definitions = repo.load_equipment()
        self.assertIn("equip.weapon.bronze_blade", definitions)
        self.assertEqual(definitions["equip.weapon.bronze_blade"].slot_type, "weapon")
        self.assertEqual(definitions["equip.armor.leather_jacket"].stat_modifiers["def"], 3)
        self.assertTrue(definitions["equip.armor.antivenom_charm"].passive_effects)
        self.assertEqual(
            definitions["equip.armor.antivenom_charm"].passive_effects[0].passive_type,
            "status_resistance",
        )

    def test_load_inn_definitions(self) -> None:
        repo = AppMasterDataRepository(Path("data/master"))
        inns = repo.load_inns()
        self.assertIn("inn.astel.seaside_inn", inns)
        self.assertEqual(inns["inn.astel.seaside_inn"].stay_price, 120)
        self.assertTrue(inns["inn.astel.seaside_inn"].revive_knocked_out_members)

    def test_resolve_final_stats_weapon_and_armor(self) -> None:
        repo = AppMasterDataRepository(Path("data/master"))
        service = EquipmentService(repo.load_equipment())
        member = PartyMemberState(
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
                "weapon": "equip.weapon.iron_blade",
                "armor": "equip.armor.leather_jacket",
            },
        )
        final = service.resolve_final_stats(member)
        self.assertEqual(final["max_hp"], 132)
        self.assertEqual(final["atk"], 32)
        self.assertEqual(final["defense"], 19)
        self.assertEqual(final["spd"], 17)


    def test_equipped_passive_summary(self) -> None:
        repo = AppMasterDataRepository(Path("data/master"))
        service = EquipmentService(repo.load_equipment())
        summary = service.passive_summary({"weapon": "equip.weapon.prayer_staff"})
        self.assertTrue(any("heal_bonus" in line for line in summary))

if __name__ == "__main__":
    unittest.main()
