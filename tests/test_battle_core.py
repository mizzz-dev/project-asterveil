from __future__ import annotations

import unittest
from pathlib import Path

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
        self.enemy = self.repo.load_enemy("enemy.ch01.port_wraith")
        self.session = BattleSession.from_definitions([self.player], [self.enemy], self.skills, self.effects)
        self.session.bind_unit_skills({
            self.player.id: self.player.skill_ids,
            self.enemy.id: self.enemy.skill_ids,
        })

    def test_initialization_from_master_data(self) -> None:
        self.assertIn(self.player.id, self.session.state.combatants)
        self.assertIn(self.enemy.id, self.session.state.combatants)
        self.assertEqual(self.session.state.combatants[self.player.id].hp, 120)

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
        target = self.session.state.combatants[self.enemy.id]
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


if __name__ == "__main__":
    unittest.main()
