from __future__ import annotations

from game.shop.domain.entities import PurchaseResult, ShopDefinition


class ShopService:
    def __init__(self, shops: dict[str, ShopDefinition], item_definitions: dict[str, dict]) -> None:
        self._shops = shops
        self._item_definitions = item_definitions

    def list_entries(self, shop_id: str) -> tuple[bool, str, ShopDefinition | None]:
        shop = self._shops.get(shop_id)
        if shop is None:
            return False, f"shop_not_found:{shop_id}", None
        return True, "ok", shop

    def purchase(self, *, inventory_state: dict, shop_id: str, item_id: str, quantity: int = 1) -> PurchaseResult:
        if quantity <= 0:
            return PurchaseResult(
                success=False,
                code="invalid_quantity",
                message=f"purchase_failed:invalid_quantity:{quantity}",
                shop_id=shop_id,
                item_id=item_id,
                quantity=quantity,
            )

        shop = self._shops.get(shop_id)
        if shop is None:
            return PurchaseResult(
                success=False,
                code="shop_not_found",
                message=f"purchase_failed:shop_not_found:{shop_id}",
                shop_id=shop_id,
                item_id=item_id,
                quantity=quantity,
            )

        entry = next((candidate for candidate in shop.entries if candidate.item_id == item_id), None)
        if entry is None:
            return PurchaseResult(
                success=False,
                code="item_not_sold",
                message=f"purchase_failed:item_not_sold:{shop_id}:{item_id}",
                shop_id=shop_id,
                item_id=item_id,
                quantity=quantity,
            )

        if item_id not in self._item_definitions:
            return PurchaseResult(
                success=False,
                code="item_not_defined",
                message=f"purchase_failed:item_not_defined:{item_id}",
                shop_id=shop_id,
                item_id=item_id,
                quantity=quantity,
            )

        if entry.price < 0:
            return PurchaseResult(
                success=False,
                code="invalid_price",
                message=f"purchase_failed:invalid_price:{item_id}:{entry.price}",
                shop_id=shop_id,
                item_id=item_id,
                quantity=quantity,
            )

        required_gold = entry.price * quantity
        owned_gold = int(inventory_state.get("gold", 0))
        if owned_gold < required_gold:
            return PurchaseResult(
                success=False,
                code="insufficient_gold",
                message=f"purchase_failed:insufficient_gold:required={required_gold}:owned={owned_gold}",
                shop_id=shop_id,
                item_id=item_id,
                quantity=quantity,
                remaining_gold=owned_gold,
            )

        inventory_state["gold"] = owned_gold - required_gold
        items = inventory_state.setdefault("items", {})
        items[item_id] = int(items.get(item_id, 0)) + quantity

        return PurchaseResult(
            success=True,
            code="purchased",
            message=(
                f"purchase_succeeded:{shop_id}:{item_id}:qty={quantity}:spent={required_gold}:"
                f"gold={inventory_state['gold']}"
            ),
            shop_id=shop_id,
            item_id=item_id,
            quantity=quantity,
            spent_gold=required_gold,
            remaining_gold=int(inventory_state["gold"]),
        )
