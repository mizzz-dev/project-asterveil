from __future__ import annotations

import unittest
from pathlib import Path

from game.shop.domain.entities import ShopDefinition, ShopEntry
from game.shop.domain.services import ShopService
from game.shop.infrastructure.master_data_repository import ShopMasterDataRepository


class ShopSliceTests(unittest.TestCase):
    def test_load_shop_definitions(self) -> None:
        repo = ShopMasterDataRepository(Path("data/master"))
        shops = repo.load_shops()

        self.assertIn("shop.astel.general_store", shops)
        entry_ids = {entry.item_id for entry in shops["shop.astel.general_store"].entries}
        self.assertEqual(
            entry_ids,
            {
                "item.consumable.mini_potion",
                "item.consumable.focus_drop",
                "item.consumable.antidote_leaf",
                "equip.weapon.iron_blade",
                "equip.armor.leather_jacket",
                "equip.armor.antivenom_charm",
                "equip.weapon.prayer_staff",
                "equip.armor.vanguard_emblem",
            },
        )

    def test_purchase_success_and_failures(self) -> None:
        shops = {
            "shop.test": ShopDefinition(
                shop_id="shop.test",
                name="test",
                entries=(ShopEntry(item_id="item.consumable.mini_potion", price=50),),
            )
        }
        item_definitions = {"item.consumable.mini_potion": {"name": "ミニポーション"}}
        service = ShopService(shops, item_definitions)
        inventory_state = {"gold": 120, "items": {}}

        success = service.purchase(
            inventory_state=inventory_state,
            shop_id="shop.test",
            item_id="item.consumable.mini_potion",
        )
        self.assertTrue(success.success)
        self.assertEqual(inventory_state["gold"], 70)
        self.assertEqual(inventory_state["items"]["item.consumable.mini_potion"], 1)

        not_enough = service.purchase(
            inventory_state=inventory_state,
            shop_id="shop.test",
            item_id="item.consumable.mini_potion",
            quantity=2,
        )
        self.assertFalse(not_enough.success)
        self.assertEqual(not_enough.code, "insufficient_gold")

        invalid_shop = service.purchase(
            inventory_state=inventory_state,
            shop_id="shop.none",
            item_id="item.consumable.mini_potion",
        )
        self.assertFalse(invalid_shop.success)
        self.assertEqual(invalid_shop.code, "shop_not_found")

        invalid_item = service.purchase(
            inventory_state=inventory_state,
            shop_id="shop.test",
            item_id="item.unknown",
        )
        self.assertFalse(invalid_item.success)
        self.assertEqual(invalid_item.code, "item_not_sold")

    def test_item_defined_validation(self) -> None:
        shops = {
            "shop.test": ShopDefinition(
                shop_id="shop.test",
                name="test",
                entries=(ShopEntry(item_id="item.consumable.mini_potion", price=10),),
            )
        }
        service = ShopService(shops, item_definitions={})
        inventory_state = {"gold": 100, "items": {}}

        result = service.purchase(
            inventory_state=inventory_state,
            shop_id="shop.test",
            item_id="item.consumable.mini_potion",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.code, "item_not_defined")


if __name__ == "__main__":
    unittest.main()
