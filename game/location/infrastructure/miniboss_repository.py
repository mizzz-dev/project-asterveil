from __future__ import annotations

import json
from pathlib import Path

from game.location.domain.miniboss_entities import MinibossDefinition, MinibossRewardItem


class MinibossMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_definitions(self, *, valid_item_ids: set[str], valid_encounter_ids: set[str]) -> dict[str, MinibossDefinition]:
        path = self._root / "miniboss_encounters.sample.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        definitions: dict[str, MinibossDefinition] = {}
        for row in raw:
            for field_name in [
                "miniboss_id",
                "encounter_id",
                "location_id",
                "trigger_event_id",
                "display_name",
                "defeat_flag",
            ]:
                if not row.get(field_name):
                    raise ValueError(f"miniboss_encounters.sample.json missing field={field_name}")
            miniboss_id = str(row["miniboss_id"])
            encounter_id = str(row["encounter_id"])
            if encounter_id not in valid_encounter_ids:
                raise ValueError(f"miniboss_encounters.sample.json unknown encounter_id={encounter_id}")
            first_clear_rewards = self._parse_rewards(
                row.get("first_clear_rewards", []),
                valid_item_ids=valid_item_ids,
                source=f"miniboss_id={miniboss_id}:first_clear_rewards",
            )
            repeat_rewards = self._parse_rewards(
                row.get("repeat_rewards", []),
                valid_item_ids=valid_item_ids,
                source=f"miniboss_id={miniboss_id}:repeat_rewards",
            )
            definitions[miniboss_id] = MinibossDefinition(
                miniboss_id=miniboss_id,
                encounter_id=encounter_id,
                location_id=str(row["location_id"]),
                trigger_event_id=str(row["trigger_event_id"]),
                display_name=str(row["display_name"]),
                first_clear_rewards=first_clear_rewards,
                repeat_rewards=repeat_rewards,
                defeat_flag=str(row["defeat_flag"]),
                repeatable=bool(row.get("repeatable", False)),
                description=str(row.get("description", "")),
            )
        return definitions

    def _parse_rewards(self, rewards: list[dict], *, valid_item_ids: set[str], source: str) -> tuple[MinibossRewardItem, ...]:
        result: list[MinibossRewardItem] = []
        for reward in rewards:
            item_id = str(reward.get("item_id") or "")
            amount = int(reward.get("amount", 0))
            if not item_id:
                raise ValueError(f"miniboss reward missing item_id: {source}")
            if item_id not in valid_item_ids:
                raise ValueError(f"miniboss reward has unknown item_id={item_id}: {source}")
            if amount <= 0:
                raise ValueError(f"miniboss reward amount must be > 0 amount={amount}: {source}")
            result.append(MinibossRewardItem(item_id=item_id, amount=amount))
        return tuple(result)
