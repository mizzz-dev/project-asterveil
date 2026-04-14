from __future__ import annotations

import random

from game.gathering.domain.entities import GatheringNodeDefinition, GatheringNodeStatus, GatheringResult


class GatheringService:
    def __init__(
        self,
        node_definitions: dict[str, GatheringNodeDefinition],
        *,
        rng: random.Random | None = None,
    ) -> None:
        self._node_definitions = node_definitions
        self._rng = rng or random.Random()

    def list_nodes(
        self,
        *,
        location_id: str,
        world_flags: set[str],
        gathered_node_ids: set[str],
    ) -> list[GatheringNodeStatus]:
        statuses: list[GatheringNodeStatus] = []
        for node in sorted(self._node_definitions.values(), key=lambda value: value.node_id):
            if node.location_id != location_id:
                continue
            unlocked = self._is_unlocked(node, world_flags)
            gathered = node.node_id in gathered_node_ids
            can_gather = unlocked and (node.repeatable or not gathered)
            statuses.append(
                GatheringNodeStatus(
                    node_id=node.node_id,
                    location_id=node.location_id,
                    name=node.name,
                    node_type=node.node_type,
                    description=node.description,
                    repeatable=node.repeatable,
                    gathered=gathered,
                    can_gather=can_gather,
                )
            )
        return statuses

    def gather(
        self,
        *,
        node_id: str,
        current_location_id: str,
        world_flags: set[str],
        gathered_node_ids: set[str],
    ) -> GatheringResult:
        node = self._node_definitions.get(node_id)
        if node is None:
            return GatheringResult(False, "invalid_node", f"gather_failed:invalid_node:{node_id}", node_id, {})
        if node.location_id != current_location_id:
            return GatheringResult(
                False,
                "location_mismatch",
                f"gather_failed:location_mismatch:required={node.location_id}:current={current_location_id}",
                node_id,
                {},
            )
        if not self._is_unlocked(node, world_flags):
            return GatheringResult(False, "locked", f"gather_failed:locked:{node_id}", node_id, {})
        if not node.repeatable and node_id in gathered_node_ids:
            return GatheringResult(False, "already_gathered", f"gather_failed:already_gathered:{node_id}", node_id, {})

        rewards = self.resolve_rewards(node)
        if not node.repeatable:
            gathered_node_ids.add(node_id)
        return GatheringResult(True, "gathered", f"gathered:{node_id}", node_id, rewards)

    def resolve_rewards(self, node: GatheringNodeDefinition) -> dict[str, int]:
        rewards: dict[str, int] = {}
        for entry in node.loot_entries:
            if entry.drop_type == "guaranteed":
                rewards[entry.item_id] = rewards.get(entry.item_id, 0) + entry.quantity
                continue
            chance = 0.0 if entry.chance is None else float(entry.chance)
            if self._rng.random() <= chance:
                rewards[entry.item_id] = rewards.get(entry.item_id, 0) + entry.quantity
        return rewards

    def _is_unlocked(self, node: GatheringNodeDefinition, world_flags: set[str]) -> bool:
        if not node.unlock_flags:
            return True
        return set(node.unlock_flags).issubset(world_flags)
