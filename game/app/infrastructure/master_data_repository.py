from __future__ import annotations

import json
from pathlib import Path

from game.app.application.reward_services import BattleReward, RewardBundle, RewardItem


class AppMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_items(self) -> dict[str, dict]:
        raw = json.loads((self._root / "items.sample.json").read_text(encoding="utf-8"))
        items: dict[str, dict] = {}
        for item in raw:
            item_id = str(item.get("item_id") or item.get("id") or "")
            if not item_id:
                raise ValueError("items.sample.json missing field=item_id")
            for field in ["category", "name"]:
                if field not in item:
                    raise ValueError(f"items.sample.json missing field={field} item={item_id}")

            normalized = dict(item)
            normalized["id"] = item_id
            normalized["item_id"] = item_id
            items[item_id] = normalized
        return items

    def load_battle_rewards(self, valid_item_ids: set[str]) -> dict[str, BattleReward]:
        raw = json.loads((self._root / "reward_tables.sample.json").read_text(encoding="utf-8"))
        rewards: dict[str, BattleReward] = {}
        for reward in raw.get("battle_rewards", []):
            encounter_id = reward.get("encounter_id")
            if not encounter_id:
                raise ValueError("reward_tables.sample.json battle_rewards missing encounter_id")
            item_rewards = tuple(
                self._validate_reward_item(item, valid_item_ids, source=f"encounter={encounter_id}")
                for item in reward.get("items", [])
            )
            rewards[encounter_id] = BattleReward(
                encounter_id=encounter_id,
                rewards_on_win=RewardBundle(
                    exp=int(reward.get("exp", 0)),
                    gold=int(reward.get("gold", 0)),
                    items=item_rewards,
                ),
            )
        return rewards

    def _validate_reward_item(self, item: dict, valid_item_ids: set[str], source: str) -> RewardItem:
        for field in ["item_id", "amount"]:
            if field not in item:
                raise ValueError(f"reward item missing field={field}: {source}")
        item_id = str(item["item_id"])
        if item_id not in valid_item_ids:
            raise ValueError(f"unknown item_id in rewards: {item_id} ({source})")
        amount = int(item["amount"])
        if amount <= 0:
            raise ValueError(f"item amount must be > 0: {amount} ({source})")
        return RewardItem(item_id=item_id, amount=amount)
