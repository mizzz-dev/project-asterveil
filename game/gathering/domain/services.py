from __future__ import annotations

import random
from typing import Callable

from game.gathering.domain.entities import (
    GatheringNodeDefinition,
    GatheringNodeStatus,
    GatheringResult,
)


class GatheringService:
    def __init__(self, roll_provider: Callable[[], float] | None = None) -> None:
        self._roll_provider = roll_provider or random.random

    def list_nodes_for_location(
        self,
        *,
        nodes: dict[str, GatheringNodeDefinition],
        location_id: str,
        world_flags: set[str],
        gathered_node_ids: set[str],
    ) -> list[GatheringNodeStatus]:
        result: list[GatheringNodeStatus] = []
        for node in sorted(nodes.values(), key=lambda entry: entry.node_id):
            if node.location_id != location_id:
                continue
            can_gather, reason_code = self.can_gather(
                node=node,
                current_location_id=location_id,
                world_flags=world_flags,
                gathered_node_ids=gathered_node_ids,
            )
            result.append(
                GatheringNodeStatus(
                    node_id=node.node_id,
                    location_id=node.location_id,
                    name=node.name,
                    node_type=node.node_type,
                    description=node.description,
                    can_gather=can_gather,
                    reason_code=reason_code,
                    is_gathered=node.node_id in gathered_node_ids,
                )
            )
        return result

    def can_gather(
        self,
        *,
        node: GatheringNodeDefinition,
        current_location_id: str,
        world_flags: set[str],
        gathered_node_ids: set[str],
    ) -> tuple[bool, str]:
        if node.location_id != current_location_id:
            return False, "location_mismatch"
        if any(flag_id not in world_flags for flag_id in node.unlock_flags):
            return False, "locked_by_flag"
        if not node.repeatable and node.node_id in gathered_node_ids:
            return False, "already_gathered"
        return True, "ok"

    def resolve_loot(self, *, node: GatheringNodeDefinition) -> dict[str, int]:
        gathered: dict[str, int] = {}
        for entry in node.loot_entries:
            amount = 0
            if entry.drop_type == "guaranteed":
                amount = entry.quantity
            elif entry.drop_type == "chance":
                if entry.chance is None:
                    raise ValueError(f"gathering node chance missing node_id={node.node_id} item_id={entry.item_id}")
                if self._roll_provider() <= entry.chance:
                    amount = entry.quantity
            else:
                raise ValueError(f"unsupported drop_type={entry.drop_type} node_id={node.node_id}")
            if amount <= 0:
                continue
            gathered[entry.item_id] = gathered.get(entry.item_id, 0) + amount
        return gathered

    def apply_to_inventory(self, *, inventory_state: dict, gained_items: dict[str, int]) -> None:
        items = inventory_state.setdefault("items", {})
        for item_id, amount in gained_items.items():
            if amount <= 0:
                continue
            items[item_id] = int(items.get(item_id, 0)) + amount

    def gather(
        self,
        *,
        node: GatheringNodeDefinition,
        current_location_id: str,
        world_flags: set[str],
        gathered_node_ids: set[str],
    ) -> GatheringResult:
        can_gather, reason_code = self.can_gather(
            node=node,
            current_location_id=current_location_id,
            world_flags=world_flags,
            gathered_node_ids=gathered_node_ids,
        )
        if not can_gather:
            return GatheringResult(
                success=False,
                code=reason_code,
                message=f"gather_failed:{reason_code}:{node.node_id}",
                node_id=node.node_id,
            )

        gained_items = self.resolve_loot(node=node)
        if not node.repeatable:
            gathered_node_ids.add(node.node_id)

        return GatheringResult(
            success=True,
            code="gathered",
            message=f"gathered:{node.node_id}",
            node_id=node.node_id,
            gained_items=gained_items,
        )
