from __future__ import annotations

from game.location.domain.treasure_entities import TreasureNodeDefinition, TreasureNodeStatus, TreasureResult


class TreasureService:
    def list_nodes_for_location(
        self,
        *,
        nodes: dict[str, TreasureNodeDefinition],
        location_id: str,
        world_flags: set[str],
        opened_node_ids: set[str],
        facility_levels: dict[str, int],
    ) -> list[TreasureNodeStatus]:
        result: list[TreasureNodeStatus] = []
        for node in sorted(nodes.values(), key=lambda value: value.reward_node_id):
            if node.location_id != location_id:
                continue
            can_open, reason_code = self.can_open(
                node=node,
                current_location_id=location_id,
                world_flags=world_flags,
                opened_node_ids=opened_node_ids,
                facility_levels=facility_levels,
            )
            result.append(
                TreasureNodeStatus(
                    reward_node_id=node.reward_node_id,
                    location_id=node.location_id,
                    name=node.name,
                    node_type=node.node_type,
                    can_open=can_open,
                    reason_code=reason_code,
                    is_opened=node.reward_node_id in opened_node_ids,
                )
            )
        return result

    def can_open(
        self,
        *,
        node: TreasureNodeDefinition,
        current_location_id: str,
        world_flags: set[str],
        opened_node_ids: set[str],
        facility_levels: dict[str, int],
    ) -> tuple[bool, str]:
        if node.location_id != current_location_id:
            return False, "location_mismatch"
        if node.one_time and node.reward_node_id in opened_node_ids:
            return False, "already_opened"
        if any(flag_id not in world_flags for flag_id in node.required_flags):
            return False, "required_flag_missing"
        if node.required_facility_id:
            current_level = int(facility_levels.get(node.required_facility_id, 0))
            if current_level < node.required_facility_level:
                return False, "required_facility_level_missing"
        return True, "ok"

    def resolve_contents(self, *, node: TreasureNodeDefinition) -> tuple[dict[str, int], tuple[str, ...]]:
        gained: dict[str, int] = {}
        content_types: set[str] = set()
        for content in node.contents:
            inventory_item_id = content.inventory_item_id
            if not inventory_item_id:
                raise ValueError(f"treasure content has no inventory_item_id reward_node_id={node.reward_node_id}")
            if content.quantity <= 0:
                raise ValueError(
                    f"treasure content quantity must be > 0 reward_node_id={node.reward_node_id}:item={inventory_item_id}"
                )
            gained[inventory_item_id] = gained.get(inventory_item_id, 0) + content.quantity
            content_types.add(content.content_type)
        return gained, tuple(sorted(content_types))

    def apply_to_inventory(self, *, inventory_state: dict, gained_items: dict[str, int]) -> None:
        items = inventory_state.setdefault("items", {})
        for item_id, amount in gained_items.items():
            if amount <= 0:
                continue
            items[item_id] = int(items.get(item_id, 0)) + amount

    def open_node(
        self,
        *,
        node: TreasureNodeDefinition,
        current_location_id: str,
        world_flags: set[str],
        opened_node_ids: set[str],
        facility_levels: dict[str, int],
    ) -> TreasureResult:
        can_open, reason_code = self.can_open(
            node=node,
            current_location_id=current_location_id,
            world_flags=world_flags,
            opened_node_ids=opened_node_ids,
            facility_levels=facility_levels,
        )
        if not can_open:
            return TreasureResult(
                success=False,
                code=reason_code,
                message=f"treasure_open_failed:{reason_code}:{node.reward_node_id}",
                reward_node_id=node.reward_node_id,
            )

        gained_items, content_types = self.resolve_contents(node=node)
        if node.one_time:
            opened_node_ids.add(node.reward_node_id)
        return TreasureResult(
            success=True,
            code="opened",
            message=f"treasure_opened:{node.reward_node_id}",
            reward_node_id=node.reward_node_id,
            gained_items=gained_items,
            content_types=content_types,
            message_on_open=node.message_on_open,
        )
