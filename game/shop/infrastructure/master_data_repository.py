from __future__ import annotations

import json
from pathlib import Path

from game.shop.domain.entities import ShopDefinition, ShopEntry


class ShopMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_shops(self) -> dict[str, ShopDefinition]:
        raw = json.loads((self._root / "shops.sample.json").read_text(encoding="utf-8"))
        shops: dict[str, ShopDefinition] = {}
        for shop_raw in raw:
            shop_id = str(shop_raw.get("shop_id") or "")
            if not shop_id:
                raise ValueError("shops.sample.json missing field=shop_id")
            if "name" not in shop_raw:
                raise ValueError(f"shops.sample.json missing field=name shop_id={shop_id}")
            entries_raw = shop_raw.get("entries")
            if not isinstance(entries_raw, list):
                raise ValueError(f"shops.sample.json entries must be list shop_id={shop_id}")

            entries: list[ShopEntry] = []
            for index, entry_raw in enumerate(entries_raw):
                item_id = str(entry_raw.get("item_id") or "")
                if not item_id:
                    raise ValueError(f"shop entry missing field=item_id shop_id={shop_id} index={index}")
                if "price" not in entry_raw:
                    raise ValueError(f"shop entry missing field=price shop_id={shop_id} item_id={item_id}")
                price = int(entry_raw["price"])
                stock_type = str(entry_raw.get("stock_type", "unlimited"))
                stock_limit = entry_raw.get("stock_limit")
                if stock_limit is not None:
                    stock_limit = int(stock_limit)
                entries.append(
                    ShopEntry(
                        item_id=item_id,
                        price=price,
                        stock_type=stock_type,
                        stock_limit=stock_limit,
                        description=str(entry_raw.get("description", "")),
                    )
                )

            shops[shop_id] = ShopDefinition(
                shop_id=shop_id,
                name=str(shop_raw["name"]),
                description=str(shop_raw.get("description", "")),
                entries=tuple(entries),
            )
        return shops
