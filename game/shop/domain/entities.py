from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopEntry:
    item_id: str
    price: int
    stock_type: str = "unlimited"
    stock_limit: int | None = None
    description: str = ""


@dataclass(frozen=True)
class ShopDefinition:
    shop_id: str
    name: str
    entries: tuple[ShopEntry, ...]
    description: str = ""


@dataclass(frozen=True)
class PurchaseResult:
    success: bool
    code: str
    message: str
    shop_id: str
    item_id: str
    quantity: int
    spent_gold: int = 0
    remaining_gold: int = 0
