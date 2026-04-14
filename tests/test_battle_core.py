from __future__ import annotations

import unittest
from pathlib import Path

from game.battle.application.equipment_passive_service import EquipmentPassiveService
from game.battle.application.session import BattleSession
from game.battle.domain.entities import ActionCommand, Team
from game.battle.domain.services import BattleState, apply_action
from game.battle.infrastructure.master_data_repository import MasterDataRepository


class BattleCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = MasterDataRepository(Path("data/master"))
        self.skills = self.repo.load_skills()
        self.effects = self.repo.load_status_effects()
        self.player = self.repo.load_character("char.main.rion")
        self.enemies, _ = self.repo.build_enemy_party("encounter.ch01.port_wraith")
        self.enemy = self.enemies[0]
        self.session = BattleSession.from_definitions([self.player], self.enemies, self.skills, self.effects)
        self.session.bind_unit_skills({
            self.player.id: self.player.skill_ids,
            **{enemy.id: enemy.skill_ids for enemy in self.enemies},
        })

    def test_initialization_from_master_data(self) -> None:
        self.assertIn(self.player.id, self.session.state.combatants)
        self.assertGreaterEqual(len([enemy for enemy in self.enemies if enemy.team == Team.ENEMY]), 2)
        self.assertEqual(self.session.state.combatants[self.player.id].hp, 120)
        self.assertEqual(self.skills["skill.striker.first_aid"].target_scope, "single_ally")
        self.assertEqual(self.skills["skill.striker.cleanse"].effect_kind, "cure_effect")

    def test_load_multi_enemy_encounters(self) -> None:
        encounters = self.repo.load_encounters()
        self.assertIn("encounter.ch01.port_wraith_single", encounters)
        self.assertEqual(encounters["encounter.ch01.port_wraith"].enemies[0].count, 2)
        self.assertEqual(len(encounters["encounter.ch01.harbor_miasma_patrol"].enemies), 2)

    def test_build_enemy_party_assigns_unique_runtime_ids_and_source_ids(self) -> None:
        enemies, runtime_to_enemy_id = self.repo.build_enemy_party("encounter.ch01.harbor_miasma_patrol")
        runtime_ids = [enemy.id for enemy in enemies]

        self.assertEqual(len(runtime_ids), 3)
        self.assertEqual(len(set(runtime_ids)), 3)
        self.assertEqual(
            sorted(runtime_to_enemy_id.values()),
            ["enemy.ch01.brine_slime", "enemy.ch01.brine_slime", "enemy.ch01.port_wraith"],
        )

    def test_normal_attack_reduces_hp(self) -> None:
        state = self.session.state
        attacker = state.combatants[self.player.id]
        target = state.combatants[self.enemy.id]
        hp_before = target.hp
        apply_action(
            state,
            ActionCommand(actor_id=attacker.unit_id, action_type="attack", target_id=target.unit_id),
            self.skills,
            self.effects,
        )
        self.assertLess(target.hp, hp_before)

    def test_skill_use_consumes_sp_and_deals_damage(self) -> None:
        state = self.session.state
        attacker = state.combatants[self.player.id]
        target = state.combatants[self.enemy.id]
        attacker.sp = 100
        hp_before = target.hp
        sp_before = attacker.sp

        result = apply_action(
            state,
            ActionCommand(
                actor_id=attacker.unit_id,
                action_type="skill",
                target_id=target.unit_id,
                skill_id="skill.striker.flare_slash",
            ),
            self.skills,
            self.effects,
        )
        self.assertLess(target.hp, hp_before)
        self.assertEqual(attacker.sp, sp_before - 12)
        self.assertEqual(result.skill_id, "skill.striker.flare_slash")

    def test_dead_when_hp_zero_or_less(self) -> None:
        target = self.session.state.combatants[self.enemy.id]
        target.apply_damage(9999)
        self.assertEqual(target.hp, 0)
        self.assertFalse(target.alive)

    def test_victory_judgement_when_enemy_annihilated(self) -> None:
        for target in [c for c in self.session.state.combatants.values() if c.team == Team.ENEMY]:
            target.apply_damage(9999)
        self.assertEqual(self.session.state.winner(), Team.PLAYER)

    def test_turn_order_depends_on_speed(self) -> None:
        order = self.session.state.turn_order()
        self.assertEqual(order[0], self.player.id)

    def test_skill_applies_debuff_and_changes_damage(self) -> None:
        state = self.session.state
        actor = state.combatants[self.player.id]
        target = state.combatants[self.enemy.id]
        actor.sp = 200

        baseline = apply_action(
            state,
            ActionCommand(actor_id=actor.unit_id, action_type="attack", target_id=target.unit_id),
            self.skills,
            self.effects,
        ).damage

        apply_action(
            state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=target.unit_id,
                skill_id="skill.striker.flare_slash",
            ),
            self.skills,
            self.effects,
        )
        boosted = apply_action(
            state,
            ActionCommand(actor_id=actor.unit_id, action_type="attack", target_id=target.unit_id),
            self.skills,
            self.effects,
        ).damage
        self.assertGreater(boosted, baseline)

    def test_poison_ticks_and_expires(self) -> None:
        state = self.session.state
        actor = state.combatants[self.enemy.id]
        target = state.combatants[self.player.id]
        actor.sp = 200
        hp_before = target.hp

        apply_action(
            state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=target.unit_id,
                skill_id="skill.enemy.venom_bite",
            ),
            self.skills,
            self.effects,
        )
        for _ in range(4):
            self.session.step_round()
        self.assertLess(target.hp, hp_before)
        self.assertTrue(all(effect.effect_id != "effect.ailment.poison" for effect in target.active_effects))

    def test_single_target_requires_living_target(self) -> None:
        state = self.session.state
        actor = state.combatants[self.player.id]
        target = state.combatants[self.enemy.id]
        actor.sp = 200
        target.apply_damage(9999)

        with self.assertRaisesRegex(ValueError, "撃破済み対象"):
            apply_action(
                state,
                ActionCommand(
                    actor_id=actor.unit_id,
                    action_type="skill",
                    target_id=target.unit_id,
                    skill_id="skill.striker.flare_slash",
                ),
                self.skills,
                self.effects,
            )

    def test_all_enemy_skill_rejects_target_id(self) -> None:
        state = self.session.state
        actor = state.combatants[self.player.id]
        actor.sp = 200
        target = next(c for c in state.combatants.values() if c.team == Team.ENEMY)

        with self.assertRaisesRegex(ValueError, "all_enemies"):
            apply_action(
                state,
                ActionCommand(
                    actor_id=actor.unit_id,
                    action_type="skill",
                    target_id=target.unit_id,
                    skill_id="skill.striker.arc_wave",
                ),
                self.skills,
                self.effects,
            )

    def test_all_enemy_skill_can_limit_target_count(self) -> None:
        state = BattleState(combatants={unit_id: combatant for unit_id, combatant in self.session.state.combatants.items()})
        actor = state.combatants[self.player.id]
        actor.sp = 200
        limited_skills = dict(self.skills)
        limited_skills["skill.test.arc_wave_two"] = self.skills["skill.striker.arc_wave"].__class__(
            id="skill.test.arc_wave_two",
            target_type="all",
            target_scope="all_enemies",
            effect_kind="damage",
            sp_cost=0,
            power=0.95,
            target_count=2,
            apply_effect_ids=tuple(),
        )
        living_enemy_ids = [
            c.unit_id for c in sorted(state.combatants.values(), key=lambda c: c.unit_id) if c.team == Team.ENEMY and c.alive
        ]

        result = apply_action(
            state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=None,
                skill_id="skill.test.arc_wave_two",
            ),
            limited_skills,
            self.effects,
        )

        self.assertEqual(len(result.target_results), 2)
        self.assertEqual(tuple(target.target_id for target in result.target_results), tuple(living_enemy_ids[:2]))

    def test_all_enemy_skill_hits_all_living_enemies(self) -> None:
        state = self.session.state
        actor = state.combatants[self.player.id]
        actor.sp = 200
        targets = [c for c in state.combatants.values() if c.team == Team.ENEMY and c.alive]
        hp_before = {target.unit_id: target.hp for target in targets}

        result = apply_action(
            state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=None,
                skill_id="skill.striker.arc_wave",
            ),
            self.skills,
            self.effects,
        )

        self.assertEqual(len(result.target_results), len(targets))
        for target in targets:
            self.assertLess(target.hp, hp_before[target.unit_id])

    def test_single_ally_heal_recovers_hp_with_cap(self) -> None:
        state = self.session.state
        actor = state.combatants[self.player.id]
        actor.sp = 200
        actor.hp = 10
        hp_before = actor.hp

        result = apply_action(
            state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=actor.unit_id,
                skill_id="skill.striker.first_aid",
            ),
            self.skills,
            self.effects,
        )

        self.assertGreater(actor.hp, hp_before)
        self.assertLessEqual(actor.hp, actor.max_hp)
        self.assertEqual(result.damage, 0)
        self.assertTrue(any(log.startswith(f"heal_applied:{actor.unit_id}:") for log in result.logs))

    def test_all_ally_heal_applies_to_multiple_members(self) -> None:
        ally = self.player.__class__(
            id="char.support.test",
            team=Team.PLAYER,
            stats=self.player.stats.__class__(hp=90, atk=18, defense=15, spd=14),
            skill_ids=tuple(),
        )
        session = BattleSession.from_definitions([self.player, ally], self.enemies, self.skills, self.effects)
        session.bind_unit_skills({self.player.id: ("skill.striker.warm_prayer",), ally.id: tuple()})
        actor = session.state.combatants[self.player.id]
        actor.sp = 200
        actor.hp = 40
        target_ally = session.state.combatants[ally.id]
        target_ally.hp = 20

        result = apply_action(
            session.state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=None,
                skill_id="skill.striker.warm_prayer",
            ),
            self.skills,
            self.effects,
        )

        self.assertEqual(len(result.target_results), 2)
        self.assertGreater(actor.hp, 40)
        self.assertGreater(target_ally.hp, 20)

    def test_single_ally_cure_removes_poison(self) -> None:
        state = self.session.state
        actor = state.combatants[self.player.id]
        actor.sp = 200
        enemy_actor = state.combatants[self.enemy.id]
        enemy_actor.sp = 200
        apply_action(
            state,
            ActionCommand(
                actor_id=enemy_actor.unit_id,
                action_type="skill",
                target_id=actor.unit_id,
                skill_id="skill.enemy.venom_bite",
            ),
            self.skills,
            self.effects,
        )
        self.assertTrue(any(effect.effect_id == "effect.ailment.poison" for effect in actor.active_effects))

        result = apply_action(
            state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=actor.unit_id,
                skill_id="skill.striker.cleanse",
            ),
            self.skills,
            self.effects,
        )
        self.assertFalse(any(effect.effect_id == "effect.ailment.poison" for effect in actor.active_effects))
        self.assertTrue(any(log.startswith(f"effect_cured:{actor.unit_id}:") for log in result.logs))

    def test_all_allies_rejects_target_id(self) -> None:
        state = self.session.state
        actor = state.combatants[self.player.id]
        actor.sp = 200
        with self.assertRaisesRegex(ValueError, "all_allies"):
            apply_action(
                state,
                ActionCommand(
                    actor_id=actor.unit_id,
                    action_type="skill",
                    target_id=actor.unit_id,
                    skill_id="skill.striker.warm_prayer",
                ),
                self.skills,
                self.effects,
            )

    def test_single_ally_rejects_knocked_out_target(self) -> None:
        ally = self.player.__class__(
            id="char.support.test",
            team=Team.PLAYER,
            stats=self.player.stats.__class__(hp=90, atk=18, defense=15, spd=14),
            skill_ids=tuple(),
        )
        session = BattleSession.from_definitions([self.player, ally], self.enemies, self.skills, self.effects)
        session.bind_unit_skills({self.player.id: ("skill.striker.first_aid",), ally.id: tuple()})
        actor = session.state.combatants[self.player.id]
        actor.sp = 200
        down = session.state.combatants[ally.id]
        down.apply_damage(9999)
        with self.assertRaisesRegex(ValueError, "戦闘不能の味方"):
            apply_action(
                session.state,
                ActionCommand(
                    actor_id=actor.unit_id,
                    action_type="skill",
                    target_id=down.unit_id,
                    skill_id="skill.striker.first_aid",
                ),
                self.skills,
                self.effects,
            )

    def test_equipment_passive_blocks_poison_application(self) -> None:
        enemies, runtime_to_enemy_id = self.repo.build_enemy_party("encounter.ch01.port_wraith_single")
        session = BattleSession.create(
            [self.player],
            enemies,
            self.skills,
            self.effects,
            equipment_passive_service=EquipmentPassiveService(self.repo.load_equipment_passives()),
            unit_equipment={self.player.id: {"armor": "equip.armor.antivenom_charm"}},
            runtime_enemy_map=runtime_to_enemy_id,
        )
        actor = session.state.combatants[enemies[0].id]
        target = session.state.combatants[self.player.id]
        actor.sp = 200

        result = apply_action(
            session.state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=target.unit_id,
                skill_id="skill.enemy.venom_bite",
            ),
            self.skills,
            self.effects,
            equipment_passive_service=session.equipment_passive_service,
            unit_passives=session.unit_passives,
        )

        self.assertTrue(any(log.startswith(f"status_resisted:{target.unit_id}:effect.ailment.poison") for log in result.logs))
        self.assertFalse(any(effect.effect_id == "effect.ailment.poison" for effect in target.active_effects))

    def test_equipment_passive_increases_heal_amount(self) -> None:
        service = EquipmentPassiveService(self.repo.load_equipment_passives())
        session = BattleSession.create(
            [self.player],
            self.enemies,
            self.skills,
            self.effects,
            equipment_passive_service=service,
            unit_equipment={self.player.id: {"weapon": "equip.weapon.prayer_staff"}},
        )
        actor = session.state.combatants[self.player.id]
        actor.sp = 200
        actor.hp = 20

        result = apply_action(
            session.state,
            ActionCommand(
                actor_id=actor.unit_id,
                action_type="skill",
                target_id=actor.unit_id,
                skill_id="skill.striker.first_aid",
            ),
            self.skills,
            self.effects,
            equipment_passive_service=session.equipment_passive_service,
            unit_passives=session.unit_passives,
        )

        self.assertTrue(any(log.startswith("passive_triggered:heal_bonus") for log in result.logs))
        self.assertEqual(actor.hp, 62)

    def test_equipment_passive_applies_battle_start_buff(self) -> None:
        session = BattleSession.create(
            [self.player],
            self.enemies,
            self.skills,
            self.effects,
            equipment_passive_service=EquipmentPassiveService(self.repo.load_equipment_passives()),
            unit_equipment={self.player.id: {"armor": "equip.armor.vanguard_emblem"}},
        )
        actor = session.state.combatants[self.player.id]

        self.assertTrue(any(effect.effect_id == "effect.buff.attack_up" for effect in actor.active_effects))
        self.assertTrue(any(log.startswith("passive_triggered:battle_start_effect") for log in session.opening_logs))


if __name__ == "__main__":
    unittest.main()
