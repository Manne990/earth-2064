from random import Random
from unittest import TestCase

from earch2064.core import (
    GameRules,
    accrue_turns,
    build,
    cash_action,
    explore,
    new_country,
)


class CoreTests(TestCase):
    def setUp(self) -> None:
        self.rules = GameRules(turn_interval_seconds=60)
        self.country = new_country(
            user_id=1,
            round_id=1,
            name="Testland",
            ruler="tester",
            now=1000,
            rules=self.rules,
        )

    def test_accrues_turns_up_to_cap(self) -> None:
        country, gained = accrue_turns(
            self.country,
            now=1000 + 10 * 60,
            rules=self.rules,
        )
        self.assertEqual(gained, 10)
        self.assertEqual(country.turns, self.rules.initial_turns + 10)

    def test_cash_action_spends_turns_and_produces(self) -> None:
        result = cash_action(self.country, turns=3, now=1200)
        self.assertEqual(result.country.turns, self.rules.initial_turns - 3)
        self.assertGreater(result.country.cash, self.country.cash)
        self.assertGreater(result.country.food, self.country.food)

    def test_explore_adds_land(self) -> None:
        result = explore(
            self.country,
            turns=2,
            now=1200,
            rules=self.rules,
            rng=Random(1),
        )
        self.assertEqual(result.country.turns, self.rules.initial_turns - 2)
        self.assertGreater(result.country.land, self.country.land)

    def test_build_farms_uses_land_cash_and_turns(self) -> None:
        result = build(
            self.country,
            building="farms",
            amount=10,
            now=1200,
            rules=self.rules,
        )
        self.assertEqual(result.country.farms, self.country.farms + 10)
        self.assertEqual(result.country.turns, self.rules.initial_turns - 2)
        self.assertLess(result.country.cash, self.country.cash)
