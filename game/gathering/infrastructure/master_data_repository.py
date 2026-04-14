from __future__ import annotations

import json
from pathlib import Path

from game.gathering.domain.entities import GatheringLootEntry, GatheringNodeDefinition


class GatheringNodeMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_nodes(
        self,
        *,
        valid_item_ids: set[str],
        valid_location_ids: set[str],
    ) -> dict[str, GatheringNodeDefinition]:
        raw = json.loads((self._root / "gathering_nodes.sample.json").read_text(encoding="utf-8"))
        nodes: dict[str, GatheringNodeDefinition] = {}

        for entry in raw:
            node_id = str(entry.get("node_id") or "")
            location_id = str(entry.get("location_id") or "")
            if not node_id:
                raise ValueError("gathering_nodes.sample.json missing field=node_id")
            if not location_id:
                raise ValueError(f"gathering_nodes.sample.json missing field=location_id node_id={node_id}")
            if location_id not in valid_location_ids:
                raise ValueError(f"gathering_nodes.sample.json unknown location_id={location_id} node_id={node_id}")
            if node_id in nodes:
                raise ValueError(f"gathering_nodes.sample.json duplicated node_id={node_id}")

            node_type = str(entry.get("node_type") or "")
            if not node_type:
                raise ValueError(f"gathering_nodes.sample.json missing field=node_type node_id={node_id}")

            loot_entries_raw = entry.get("loot_entries") or []
            if not loot_entries_raw:
                raise ValueError(f"gathering_nodes.sample.json loot_entries required node_id={node_id}")

            loot_entries: list[GatheringLootEntry] = []
            for loot in loot_entries_raw:
                item_id = str(loot.get("item_id") or "")
                if item_id not in valid_item_ids:
                    raise ValueError(f"gathering_nodes.sample.json unknown item_id={item_id} node_id={node_id}")
                quantity = int(loot.get("quantity", 0))
                if quantity <= 0:
                    raise ValueError(f"gathering_nodes.sample.json invalid quantity={quantity} node_id={node_id}")
                drop_type = str(loot.get("drop_type") or "")
                if drop_type not in {"guaranteed", "chance"}:
                    raise ValueError(
                        f"gathering_nodes.sample.json invalid drop_type={drop_type} node_id={node_id} item_id={item_id}"
                    )
                chance = loot.get("chance")
                if drop_type == "chance":
                    if chance is None:
                        raise ValueError(
                            f"gathering_nodes.sample.json chance required for chance drop node_id={node_id} item_id={item_id}"
                        )
                    chance = float(chance)
                    if chance < 0 or chance > 1:
                        raise ValueError(
                            f"gathering_nodes.sample.json chance must be 0-1 node_id={node_id} item_id={item_id}"
                        )
                loot_entries.append(
                    GatheringLootEntry(
                        item_id=item_id,
                        quantity=quantity,
                        drop_type=drop_type,
                        chance=float(chance) if chance is not None else None,
                    )
                )

            nodes[node_id] = GatheringNodeDefinition(
                node_id=node_id,
                location_id=location_id,
                name=str(entry.get("name") or node_id),
                node_type=node_type,
                description=str(entry.get("description") or ""),
                loot_entries=tuple(loot_entries),
                repeatable=bool(entry.get("repeatable", False)),
                unlock_flags=tuple(str(flag_id) for flag_id in entry.get("unlock_flags", [])),
            )

        return nodes
