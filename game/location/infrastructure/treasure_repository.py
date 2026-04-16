from __future__ import annotations

import json
from pathlib import Path

from game.location.domain.treasure_entities import TreasureContentDefinition, TreasureNodeDefinition


class TreasureMasterDataRepository:
    SUPPORTED_NODE_TYPES = {"treasure_chest", "discoverable_cache", "recipe_book_spot"}
    SUPPORTED_CONTENT_TYPES = {"item", "equipment", "recipe_book"}

    def __init__(self, root: Path) -> None:
        self._root = root

    def load_nodes(
        self,
        *,
        valid_item_ids: set[str],
        valid_equipment_ids: set[str],
        valid_location_ids: set[str],
    ) -> dict[str, TreasureNodeDefinition]:
        raw = json.loads((self._root / "location_rewards.sample.json").read_text(encoding="utf-8"))
        result: dict[str, TreasureNodeDefinition] = {}
        for entry in raw:
            reward_node_id = str(entry.get("reward_node_id") or "")
            if not reward_node_id:
                raise ValueError("location_rewards.sample.json missing field=reward_node_id")
            location_id = str(entry.get("location_id") or "")
            if not location_id:
                raise ValueError(f"location_rewards.sample.json missing field=location_id node_id={reward_node_id}")
            if location_id not in valid_location_ids:
                raise ValueError(f"location_rewards.sample.json unknown location_id={location_id} node_id={reward_node_id}")
            node_type = str(entry.get("node_type") or "")
            if node_type not in self.SUPPORTED_NODE_TYPES:
                raise ValueError(
                    f"location_rewards.sample.json unsupported node_type={node_type} node_id={reward_node_id}"
                )

            contents_raw = entry.get("contents") or []
            if not contents_raw:
                raise ValueError(f"location_rewards.sample.json contents required node_id={reward_node_id}")
            contents: list[TreasureContentDefinition] = []
            for content in contents_raw:
                content_type = str(content.get("content_type") or "")
                if content_type not in self.SUPPORTED_CONTENT_TYPES:
                    raise ValueError(
                        f"location_rewards.sample.json unsupported content_type={content_type} node_id={reward_node_id}"
                    )
                quantity = int(content.get("quantity", 0))
                if quantity <= 0:
                    raise ValueError(
                        f"location_rewards.sample.json quantity must be > 0 node_id={reward_node_id} content_type={content_type}"
                    )
                normalized = self._resolve_content_ids(
                    content=content,
                    content_type=content_type,
                    reward_node_id=reward_node_id,
                    valid_item_ids=valid_item_ids,
                    valid_equipment_ids=valid_equipment_ids,
                )
                contents.append(
                    TreasureContentDefinition(
                        content_type=content_type,
                        item_id=normalized.get("item_id"),
                        equipment_id=normalized.get("equipment_id"),
                        recipe_book_id=normalized.get("recipe_book_id"),
                        quantity=quantity,
                    )
                )

            facility_requirement = entry.get("required_facility_level")
            required_facility_id: str | None = None
            required_facility_level = 0
            if facility_requirement:
                required_facility_id = str(facility_requirement.get("facility_id") or "")
                required_facility_level = int(facility_requirement.get("level", 0))
                if not required_facility_id:
                    raise ValueError(
                        f"location_rewards.sample.json required_facility_level.facility_id required node_id={reward_node_id}"
                    )
                if required_facility_level <= 0:
                    raise ValueError(
                        f"location_rewards.sample.json required_facility_level.level must be > 0 node_id={reward_node_id}"
                    )

            result[reward_node_id] = TreasureNodeDefinition(
                reward_node_id=reward_node_id,
                location_id=location_id,
                name=str(entry.get("name") or reward_node_id),
                node_type=node_type,
                description=str(entry.get("description") or ""),
                contents=tuple(contents),
                one_time=bool(entry.get("one_time", True)),
                required_flags=tuple(str(flag_id) for flag_id in entry.get("required_flags", [])),
                required_facility_id=required_facility_id,
                required_facility_level=required_facility_level,
                message_on_open=str(entry.get("message_on_open") or ""),
            )
        return result

    def _resolve_content_ids(
        self,
        *,
        content: dict,
        content_type: str,
        reward_node_id: str,
        valid_item_ids: set[str],
        valid_equipment_ids: set[str],
    ) -> dict[str, str]:
        if content_type == "item":
            item_id = str(content.get("item_id") or "")
            if item_id not in valid_item_ids:
                raise ValueError(f"location_rewards.sample.json unknown item_id={item_id} node_id={reward_node_id}")
            return {"item_id": item_id}
        if content_type == "equipment":
            equipment_id = str(content.get("equipment_id") or "")
            if equipment_id not in valid_equipment_ids:
                raise ValueError(
                    f"location_rewards.sample.json unknown equipment_id={equipment_id} node_id={reward_node_id}"
                )
            return {"equipment_id": equipment_id}

        recipe_book_id = str(content.get("recipe_book_id") or "")
        if recipe_book_id not in valid_item_ids:
            raise ValueError(f"location_rewards.sample.json unknown recipe_book_id={recipe_book_id} node_id={reward_node_id}")
        return {"recipe_book_id": recipe_book_id}
