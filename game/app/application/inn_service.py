from __future__ import annotations

from dataclasses import dataclass

from game.app.application.equipment_service import EquipmentService
from game.save.domain.entities import PartyMemberState


@dataclass(frozen=True)
class InnDefinition:
    inn_id: str
    name: str
    stay_price: int
    description: str = ""
    revive_knocked_out_members: bool = True
    location_id: str = ""


@dataclass(frozen=True)
class InnStayResult:
    success: bool
    code: str
    message: str


class InnService:
    def __init__(self, inns: dict[str, InnDefinition], equipment_service: EquipmentService) -> None:
        self._inns = inns
        self._equipment_service = equipment_service

    def get_inn(self, inn_id: str) -> InnDefinition | None:
        return self._inns.get(inn_id)

    def stay(
        self,
        *,
        inn_id: str,
        party_members: list[PartyMemberState],
        inventory_state: dict,
    ) -> InnStayResult:
        inn = self._inns.get(inn_id)
        if inn is None:
            return InnStayResult(False, "inn_not_found", f"inn_stay_failed:inn_not_found:{inn_id}")
        if not party_members:
            return InnStayResult(False, "invalid_party", "inn_stay_failed:invalid_party:empty")

        gold = int(inventory_state.get("gold", 0))
        if gold < inn.stay_price:
            return InnStayResult(
                False,
                "insufficient_gold",
                f"inn_stay_failed:insufficient_gold:required={inn.stay_price}:owned={gold}",
            )

        for member in party_members:
            if member.max_hp <= 0 or member.max_sp < 0:
                return InnStayResult(
                    False,
                    "invalid_party",
                    f"inn_stay_failed:invalid_party:bad_stats:{member.character_id}",
                )

        inventory_state["gold"] = gold - inn.stay_price
        for member in party_members:
            if inn.revive_knocked_out_members:
                member.alive = True
            final = self._equipment_service.resolve_final_stats(member)
            member.current_hp = final["max_hp"]
            member.current_sp = final["max_sp"]

        return InnStayResult(
            True,
            "stayed",
            f"inn_stay_succeeded:{inn.inn_id}:spent={inn.stay_price}:gold={inventory_state['gold']}",
        )
