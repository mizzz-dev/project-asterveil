from __future__ import annotations

import json
from pathlib import Path

from game.app.application.workshop_progress_service import WorkshopOrderDefinition, WorkshopRankDefinition


class WorkshopOrderMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load(self) -> tuple[dict[str, WorkshopOrderDefinition], tuple[WorkshopRankDefinition, ...]]:
        path = self._root / "workshop_orders.sample.json"
        if not path.exists():
            return {}, tuple()
        raw = json.loads(path.read_text(encoding="utf-8"))
        orders_raw = raw.get("orders", [])
        rank_raw = raw.get("rank_levels", [])

        orders: dict[str, WorkshopOrderDefinition] = {}
        for row in orders_raw:
            order_id = str(row.get("order_id") or "")
            if not order_id:
                raise ValueError("workshop_orders.sample.json missing field=order_id")
            required_turn_in_items = tuple(
                (str(item.get("item_id")), int(item.get("quantity", 0)))
                for item in row.get("required_turn_in_items", [])
            )
            if any((not item_id or quantity <= 0) for item_id, quantity in required_turn_in_items):
                raise ValueError(f"workshop_orders.sample.json invalid required_turn_in_items order_id={order_id}")
            progress = int(row.get("workshop_progress_value", 0))
            if progress <= 0:
                raise ValueError(f"workshop_orders.sample.json workshop_progress_value must be > 0 order_id={order_id}")
            orders[order_id] = WorkshopOrderDefinition(
                order_id=order_id,
                name=str(row.get("name") or order_id),
                description=str(row.get("description") or ""),
                repeatable=bool(row.get("repeatable", False)),
                repeat_reset_rule=str(row.get("repeat_reset_rule") or "manual_reaccept"),
                required_turn_in_items=required_turn_in_items,
                require_crafted_item=bool(row.get("require_crafted_item", False)),
                workshop_progress_value=progress,
                required_workshop_level=max(1, int(row.get("required_workshop_level", 1))),
                rewards=dict(row.get("rewards", {})),
                unlock_conditions=dict(row.get("unlock_conditions", {})),
            )

        rank_definitions = tuple(
            sorted(
                (
                    WorkshopRankDefinition(
                        level=int(row.get("level", 0)),
                        required_progress=int(row.get("required_progress", 0)),
                        unlock_recipe_ids=tuple(str(recipe_id) for recipe_id in row.get("unlock_recipe_ids", [])),
                    )
                    for row in rank_raw
                ),
                key=lambda row: row.level,
            )
        )
        for idx, rank in enumerate(rank_definitions):
            if rank.level <= 0:
                raise ValueError("workshop_orders.sample.json rank level must be >= 1")
            if idx == 0 and rank.level != 1:
                raise ValueError("workshop_orders.sample.json first rank level must be 1")
            if idx > 0 and rank.level != rank_definitions[idx - 1].level + 1:
                raise ValueError("workshop_orders.sample.json rank level must be continuous")
        return orders, rank_definitions
