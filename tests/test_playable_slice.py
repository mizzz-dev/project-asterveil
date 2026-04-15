from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication
from game.quest.domain.entities import BattleResult, QuestStatus
from game.save.domain.entities import PartyActiveEffectState


class PlayableSliceTests(unittest.TestCase):
    def _build_app(self, tmp_dir: str, *, win: bool = True) -> PlayableSliceApplication:
        def battle_executor(encounter_id: str) -> BattleResult:
            self.assertEqual(encounter_id, "encounter.ch01.port_wraith")
            return BattleResult(
                encounter_id=encounter_id,
                player_won=win,
                defeated_enemy_ids=("enemy.ch01.port_wraith",) if win else tuple(),
            )

        return PlayableSliceApplication(
            master_root=Path("data/master"),
            save_file_path=Path(tmp_dir) / "slot_01.json",
            battle_executor=battle_executor,
        )

    def test_new_game_creates_initial_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            logs = app.new_game()

            self.assertIn("new_game_started", logs)
            self.assertEqual(len(app.party_members), 1)
            self.assertEqual(app.last_event_id, "event.system.new_game_intro")
            self.assertIn("flag.game.new_game_started", app.quest_session.world_flags)
            self.assertEqual(app.inventory_state["gold"], 300)
            self.assertEqual(app.inventory_state["items"]["item.consumable.mini_potion"], 3)
            self.assertEqual(app.inventory_state["items"]["item.consumable.antidote_leaf"], 1)
            self.assertEqual(app.party_members[0].unlocked_skill_ids, ["skill.striker.flare_slash"])

    def test_continue_loads_saved_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            ok, message = resumed.continue_game()

            self.assertTrue(ok)
            self.assertIn("ロード", message)
            self.assertEqual(resumed.quest_state().status, QuestStatus.IN_PROGRESS)
            self.assertEqual(resumed.inventory_state["gold"], 300)

    def test_transition_from_in_progress_to_reportable_to_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            losing_app = self._build_app(tmp_dir, win=False)
            losing_app.new_game()
            losing_app.accept_quest("quest.ch01.missing_port_record")

            self.assertEqual(losing_app.quest_state().status, QuestStatus.IN_PROGRESS)
            self.assertNotIn("hunt", {item.key for item in losing_app.available_actions()})
            losing_app.travel_to("location.field.tidal_flats")
            self.assertIn("hunt", {item.key for item in losing_app.available_actions()})

            winning_app = self._build_app(tmp_dir, win=True)
            winning_app.quest_session = losing_app.quest_session
            winning_app.party_members = losing_app.party_members
            winning_app.last_event_id = losing_app.last_event_id
            winning_app.inventory_state = losing_app.inventory_state
            winning_app.location_state = losing_app.location_state
            winning_app.party_members[0].current_exp = 440

            hunt_logs = winning_app.perform_action("hunt")
            self.assertIn("quest_status_changed:quest.ch01.missing_port_record:ready_to_complete", hunt_logs)
            self.assertEqual(winning_app.quest_state().status, QuestStatus.READY_TO_COMPLETE)
            self.assertTrue(any(log.startswith("exp_applied:") for log in hunt_logs))
            self.assertTrue(any(log.startswith("learned_skill:char.main.rion:skill.striker.venom_edge") for log in hunt_logs))
            self.assertGreater(winning_app.inventory_state["gold"], 0)

            winning_app.perform_action("report")
            self.assertEqual(winning_app.quest_state().status, QuestStatus.COMPLETED)

    def test_save_and_load_keeps_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.party_members[0].current_hp = 50
            app.use_item("item.consumable.mini_potion", "char.main.rion")
            app.accept_quest("quest.ch01.missing_port_record")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            status_logs = resumed.perform_action("status")
            inventory_logs = resumed.perform_action("inventory")

            self.assertTrue(
                any("last_event_id:event.system.quest_accepted:quest.ch01.missing_port_record" in line for line in status_logs)
            )
            self.assertEqual(resumed.quest_state().status, QuestStatus.IN_PROGRESS)
            self.assertTrue(any(line.startswith("gold:") for line in inventory_logs))
            self.assertEqual(resumed.party_members[0].current_hp, 90)
            self.assertEqual(resumed.inventory_state["items"]["item.consumable.mini_potion"], 2)

    def test_recipe_unlock_state_persists_across_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            report_logs = app.perform_action("report")
            self.assertTrue(any(line.startswith("recipe_discovered:recipe.craft.memory_edge:") for line in report_logs))

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            resumed.continue_game()

            self.assertIn("recipe.craft.memory_edge", resumed.unlocked_recipe_ids)
            craft_lines = resumed.crafting_recipe_lines()
            self.assertTrue(any("craft_recipe:recipe.craft.memory_edge" in line and "unlock=解放済み" in line for line in craft_lines))
            self.assertIn("recipe.craft.memory_edge", resumed.discovered_recipe_ids)

    def test_use_item_updates_hp_sp_and_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.party_members[0].current_hp = 60
            app.party_members[0].current_sp = 30

            hp_logs = app.use_item("item.consumable.mini_potion", "char.main.rion")
            sp_logs = app.use_item("item.consumable.focus_drop", "char.main.rion")

            self.assertIn("item_used:item.consumable.mini_potion:target=char.main.rion", hp_logs)
            self.assertIn("item_used:item.consumable.focus_drop:target=char.main.rion", sp_logs)
            self.assertEqual(app.party_members[0].current_hp, 100)
            self.assertEqual(app.party_members[0].current_sp, 55)
            self.assertEqual(app.inventory_state["items"]["item.consumable.mini_potion"], 2)
            self.assertEqual(app.inventory_state["items"]["item.consumable.focus_drop"], 1)

    def test_antidote_item_cures_status_effect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.party_members[0].active_effects = [PartyActiveEffectState("effect.ailment.poison", 2)]
            logs = app.use_item("item.consumable.antidote_leaf", "char.main.rion")
            self.assertEqual(logs, ["item_used:item.consumable.antidote_leaf:target=char.main.rion"])
            self.assertEqual(app.party_members[0].active_effects, [])

    def test_use_item_failure_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            no_stock = app.use_item("item.consumable.unknown", "char.main.rion")
            self.assertEqual(no_stock, ["item_use_failed:no_stock:item.consumable.unknown"])

            invalid_target = app.use_item("item.consumable.mini_potion", "char.main.unknown")
            self.assertEqual(invalid_target, ["item_use_failed:invalid_target:char.main.unknown"])

            app.inventory_state["items"]["item.consumable.focus_drop"] = 0
            out_of_stock = app.use_item("item.consumable.focus_drop", "char.main.rion")
            self.assertEqual(out_of_stock, ["item_use_failed:no_stock:item.consumable.focus_drop"])

    def test_status_and_usable_item_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            logs = app.perform_action("status")
            usable = app.perform_action("use_item")
            self.assertTrue(any(line.startswith("member:char.main.rion") for line in logs))
            self.assertTrue(any("skills=['skill.striker.flare_slash']" in line for line in logs))
            self.assertTrue(any(line.startswith("usable_item:item.consumable.mini_potion") for line in usable))

    def test_shop_purchase_updates_inventory_and_gold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            catalog = app.perform_action("shop")
            self.assertTrue(any(line.startswith("shop:shop.astel.general_store") for line in catalog))
            self.assertTrue(any(line.startswith("shop_item:item.consumable.mini_potion") for line in catalog))
            self.assertTrue(any(line.startswith("shop_item:equip.weapon.iron_blade") for line in catalog))

            result = app.buy_item("item.consumable.mini_potion")
            self.assertEqual(
                result,
                ["purchase_succeeded:shop.astel.general_store:item.consumable.mini_potion:qty=1:spent=50:gold=250"],
            )
            self.assertEqual(app.inventory_state["gold"], 250)
            self.assertEqual(app.inventory_state["items"]["item.consumable.mini_potion"], 4)

    def test_shop_purchase_failure_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["gold"] = 10

            fail_gold = app.buy_item("item.consumable.mini_potion")
            self.assertEqual(
                fail_gold,
                ["purchase_failed:insufficient_gold:required=50:owned=10"],
            )
            fail_item = app.buy_item("item.consumable.unknown")
            self.assertEqual(
                fail_item,
                ["purchase_failed:item_not_sold:shop.astel.general_store:item.consumable.unknown"],
            )
            fail_shop = app.buy_item("item.consumable.mini_potion", shop_id="shop.unknown")
            self.assertEqual(fail_shop, ["purchase_failed:shop_not_found:shop.unknown"])

            app.inventory_state["gold"] = 100
            app.buy_item("item.consumable.focus_drop")
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            self.assertEqual(resumed.inventory_state["gold"], 55)
            self.assertEqual(resumed.inventory_state["items"]["item.consumable.focus_drop"], 3)

            resumed.party_members[0].current_sp = 40
            use_logs = resumed.use_item("item.consumable.focus_drop", "char.main.rion")
            self.assertEqual(use_logs, ["item_used:item.consumable.focus_drop:target=char.main.rion"])

    def test_inn_stay_restores_hp_sp_and_revive_then_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.buy_item("equip.armor.leather_jacket")
            app.equip_item("char.main.rion", "armor", "equip.armor.leather_jacket")
            app.party_members[0].current_hp = 1
            app.party_members[0].current_sp = 2
            app.party_members[0].alive = False
            app.party_members[0].active_effects = [PartyActiveEffectState("effect.ailment.poison", 2)]
            app.inventory_state["gold"] = 200

            info = app.inn_info_lines()
            self.assertTrue(any(line.startswith("inn:inn.astel.seaside_inn") for line in info))
            self.assertIn("inn_stay_price:120", info)

            stay_logs = app.stay_at_inn()
            self.assertIn("inn_stay_succeeded:inn.astel.seaside_inn:spent=120:gold=80", stay_logs)
            self.assertEqual(app.inventory_state["gold"], 80)
            self.assertTrue(app.party_members[0].alive)
            self.assertEqual(app.party_members[0].current_hp, 132)
            self.assertEqual(app.party_members[0].current_sp, 100)
            self.assertEqual(app.party_members[0].active_effects, [])

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            self.assertEqual(resumed.inventory_state["gold"], 80)
            self.assertTrue(resumed.party_members[0].alive)

    def test_save_load_preserves_active_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.party_members[0].active_effects = [PartyActiveEffectState("effect.ailment.poison", 2)]
            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            self.assertEqual(len(resumed.party_members[0].active_effects), 1)
            self.assertEqual(resumed.party_members[0].active_effects[0].effect_id, "effect.ailment.poison")

    def test_inn_stay_failure_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["gold"] = 50

            no_gold = app.stay_at_inn()
            self.assertEqual(no_gold, ["inn_stay_failed:insufficient_gold:required=120:owned=50"])

            invalid_inn = app.stay_at_inn("inn.unknown")
            self.assertEqual(invalid_inn, ["inn_stay_failed:inn_not_found:inn.unknown"])

            app.party_members[0].max_hp = 0
            app.inventory_state["gold"] = 999
            invalid_party = app.stay_at_inn()
            self.assertEqual(invalid_party, ["inn_stay_failed:invalid_party:bad_stats:char.main.rion"])

    def test_equipment_flow_updates_stats_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()

            bought = app.buy_item("equip.weapon.iron_blade")
            self.assertEqual(
                bought,
                ["purchase_succeeded:shop.astel.general_store:equip.weapon.iron_blade:qty=1:spent=240:gold=60"],
            )
            equip_logs = app.equip_item("char.main.rion", "weapon", "equip.weapon.iron_blade")
            self.assertIn("equip_succeeded:char.main.rion:weapon:equip.weapon.iron_blade", equip_logs)
            self.assertTrue(any("atk=32" in line for line in equip_logs))

            app.perform_action("save")
            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            status = resumed.perform_action("status")
            self.assertTrue(any("equip.weapon.iron_blade" in line for line in status))
            self.assertTrue(any("atk=32" in line for line in status))

    def test_equipment_failure_cases_and_battle_reflection(self) -> None:
        captured: dict[str, int] = {}

        def battle_executor(encounter_id: str, party_members=None) -> BattleResult:
            self.assertEqual(encounter_id, "encounter.ch01.port_wraith")
            if party_members:
                captured["atk"] = party_members[0].atk
                captured["defense"] = party_members[0].defense
            return BattleResult(encounter_id=encounter_id, player_won=False, defeated_enemy_ids=tuple())

        with tempfile.TemporaryDirectory() as tmp_dir:
            app = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=battle_executor,
            )
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")

            invalid_id = app.equip_item("char.main.rion", "weapon", "equip.weapon.unknown")
            self.assertEqual(invalid_id, ["equip_failed:unknown_equipment:equip.weapon.unknown"])
            invalid_slot = app.equip_item("char.main.rion", "armor", "equip.weapon.bronze_blade")
            self.assertEqual(invalid_slot, ["equip_failed:slot_mismatch:armor:equip.weapon.bronze_blade"])
            no_stock = app.equip_item("char.main.rion", "armor", "equip.armor.leather_jacket")
            self.assertEqual(no_stock, ["equip_failed:insufficient_stock:equip.armor.leather_jacket"])

            app.buy_item("equip.armor.leather_jacket")
            equip = app.equip_item("char.main.rion", "armor", "equip.armor.leather_jacket")
            self.assertIn("equip_succeeded:char.main.rion:armor:equip.armor.leather_jacket", equip)
            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            self.assertEqual(captured["atk"], 28)
            self.assertEqual(captured["defense"], 19)

    def test_continue_detects_missing_or_broken_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            ok, message = app.continue_game()
            self.assertFalse(ok)
            self.assertIn("見つかりません", message)

            save_path = Path(tmp_dir) / "slot_01.json"
            save_path.write_text("{broken json", encoding="utf-8")

            ok, message = app.continue_game()
            self.assertFalse(ok)
            self.assertIn("破損", message)

    def test_quest_board_multi_quest_unlock_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            board_lines = app.quest_board_lines()
            self.assertTrue(any("quest_board_entry:quest.ch01.missing_port_record" in line for line in board_lines))
            self.assertTrue(any("quest.ch01.harbor_cleanup" in line and "status=locked" in line for line in board_lines))

            self.assertEqual(app.accept_quest("quest.ch01.missing_port_record"), ["quest_accepted:quest.ch01.missing_port_record"])
            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            app.perform_action("report")

            board_lines = app.quest_board_lines()
            self.assertTrue(any("quest.ch01.harbor_cleanup" in line and "status=available" in line for line in board_lines))
            self.assertEqual(app.accept_quest("quest.ch01.harbor_cleanup"), ["quest_accepted:quest.ch01.harbor_cleanup"])
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            resumed_board = resumed.quest_board_lines()
            self.assertTrue(
                any("quest.ch01.missing_port_record" in line and "status=completed" in line for line in resumed_board)
            )
            self.assertTrue(
                any("quest.ch01.harbor_cleanup" in line and "status=in_progress" in line for line in resumed_board)
            )

    def test_turn_in_from_gathering_item_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.inventory_state["items"]["item.consumable.antidote_leaf"] = 0
            app.accept_quest("quest.ch01.herb_supply_turn_in")

            first = app.turn_in_quest_items("quest.ch01.herb_supply_turn_in")
            self.assertEqual(first, ["turn_in_failed:insufficient_items"])

            app.gather_from_node("node.herb.astel_backyard_01")
            talk_logs = app.talk_to_npc(
                "npc.astel.guard",
                choice_selector=lambda choices, _step_id: choices[0][0],
            )

            self.assertTrue(any(line.startswith("turn_in_success:quest.ch01.herb_supply_turn_in") for line in talk_logs))
            self.assertTrue(any(line.startswith("quest_completed:quest.ch01.herb_supply_turn_in") for line in talk_logs))
            self.assertEqual(app.quest_state("quest.ch01.herb_supply_turn_in").status, QuestStatus.COMPLETED)

    def test_turn_in_from_loot_item_and_save_load_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            app.perform_action("report")
            app.accept_quest("quest.ch01.memory_fragment_delivery")
            app.travel_to("location.town.astel")

            app.inventory_state["items"]["item.material.memory_shard"] = 1
            failed_logs = app.turn_in_quest_items("quest.ch01.memory_fragment_delivery")
            self.assertEqual(failed_logs, ["turn_in_failed:insufficient_items"])

            app.inventory_state["items"]["item.material.memory_shard"] = 2
            success_logs = app.turn_in_quest_items("quest.ch01.memory_fragment_delivery")
            self.assertTrue(any(line.startswith("turn_in_success:quest.ch01.memory_fragment_delivery") for line in success_logs))
            self.assertEqual(app.quest_state("quest.ch01.memory_fragment_delivery").status, QuestStatus.READY_TO_COMPLETE)
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            resumed_state = resumed.quest_state("quest.ch01.memory_fragment_delivery")
            self.assertEqual(resumed_state.status, QuestStatus.READY_TO_COMPLETE)
            self.assertEqual(
                resumed_state.objective_item_progress["obj.ch01.turn_in_memory_shard"]["item.material.memory_shard"],
                2,
            )

    def test_repeatable_turn_in_quest_reaccept_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.accept_quest("quest.ch01.herb_supply_turn_in")
            app.turn_in_quest_items("quest.ch01.herb_supply_turn_in", auto_complete=True)
            self.assertEqual(app.quest_state("quest.ch01.herb_supply_turn_in").status, QuestStatus.COMPLETED)

            board_before_rest = app.quest_board_lines()
            self.assertTrue(
                any("quest.ch01.herb_supply_turn_in" in line and "status=repost_waiting" in line for line in board_before_rest)
            )

            rest_logs = app.stay_at_inn()
            self.assertTrue(any(line.startswith("quest_repeat_ready:on_rest:") for line in rest_logs))

            board_ready = app.quest_board_lines()
            self.assertTrue(
                any("quest.ch01.herb_supply_turn_in" in line and "status=reacceptable" in line for line in board_ready)
            )

            reaccept_logs = app.accept_quest("quest.ch01.herb_supply_turn_in")
            self.assertEqual(reaccept_logs, ["quest_reaccepted:quest.ch01.herb_supply_turn_in"])
            self.assertEqual(
                app.quest_state("quest.ch01.herb_supply_turn_in").objective_progress["obj.ch01.turn_in_antidote_leaf"],
                0,
            )

    def test_repeatable_bounty_reaccept_persists_after_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = self._build_app(tmp_dir)
            app.new_game()
            app.accept_quest("quest.ch01.missing_port_record")
            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            app.perform_action("report")

            app.accept_quest("quest.ch01.harbor_cleanup")
            app.travel_to("location.field.tidal_flats")
            app.perform_action("hunt")
            app.perform_action("report")

            waiting_board = app.quest_board_lines()
            self.assertTrue(any("quest.ch01.harbor_cleanup" in line and "status=repost_waiting" in line for line in waiting_board))

            app.travel_to("location.field.tidal_flats")
            return_logs = app.travel_to("location.town.astel")
            self.assertTrue(any(line.startswith("quest_repeat_ready:on_return_to_hub:") for line in return_logs))
            ready_board = app.quest_board_lines()
            self.assertTrue(any("quest.ch01.harbor_cleanup" in line and "status=reacceptable" in line for line in ready_board))
            app.perform_action("save")

            resumed = self._build_app(tmp_dir)
            resumed.continue_game()
            resumed_board = resumed.quest_board_lines()
            self.assertTrue(any("quest.ch01.harbor_cleanup" in line and "status=reacceptable" in line for line in resumed_board))


if __name__ == "__main__":
    unittest.main()
