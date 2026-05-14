from dataclasses import replace
from random import Random
from unittest import TestCase

from earth2064.core import (
    GameRules,
    GOVERNMENTS,
    MARKET_PRICES,
    accrue_turns,
    apply_economy,
    build,
    buy_market,
    build_rate,
    cash_action,
    canonical_building,
    canonical_government,
    canonical_tech,
    economy_for_turns,
    explore,
    government_for,
    launch_missile,
    new_country,
    produce_action,
    research,
    sell_market,
    set_industrial_allocation,
    standard_strike,
    spy_intel,
    tech_bonus,
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
        self.assertEqual(result.country.free_land, self.country.free_land - 10)

    def test_building_aliases_and_non_farm_builds(self) -> None:
        self.assertEqual(canonical_building("OIL"), "oil_rigs")
        self.assertEqual(canonical_building("EZ"), "enterprise")

        result = build(
            self.country,
            building="labs",
            amount=5,
            now=1200,
            rules=self.rules,
        )

        self.assertEqual(result.country.labs, self.country.labs + 5)
        self.assertIn("research labs", result.message)

    def test_construction_sites_increase_build_rate(self) -> None:
        low = replace(self.country, construction=0)
        high = replace(self.country, construction=80)

        self.assertGreater(build_rate(high), build_rate(low))

    def test_research_adds_technology_points(self) -> None:
        self.assertEqual(canonical_tech("business"), "business")

        result = research(
            self.country,
            tech="business",
            turns=4,
            now=1400,
            rules=self.rules,
        )

        self.assertEqual(result.country.turns, self.rules.initial_turns - 4)
        self.assertGreater(result.country.tech_business, self.country.tech_business)

    def test_technology_bonus_affects_economy(self) -> None:
        teched = replace(self.country, tech_business=5000)
        plain = economy_for_turns(self.country, 1, self.rules)
        improved = economy_for_turns(teched, 1, self.rules)

        self.assertGreater(tech_bonus(teched, "business"), 1.0)
        self.assertGreater(improved.cash_income, plain.cash_income)

    def test_produce_action_creates_military_units(self) -> None:
        result = produce_action(self.country, turns=5, now=1500, rules=self.rules)

        self.assertEqual(result.country.turns, self.rules.initial_turns - 5)
        self.assertGreater(result.country.troops, self.country.troops)
        self.assertGreater(result.country.jets, self.country.jets)

    def test_industrial_allocation_must_total_100(self) -> None:
        result = set_industrial_allocation(
            self.country,
            troops=25,
            jets=25,
            tanks=25,
            turrets=25,
            now=1500,
        )

        self.assertEqual(result.country.industrial_troops, 25)
        with self.assertRaises(ValueError):
            set_industrial_allocation(
                self.country,
                troops=20,
                jets=20,
                tanks=20,
                turrets=20,
                now=1500,
            )

    def test_market_buy_and_sell_resources(self) -> None:
        bought = buy_market(self.country, good="food", amount=100, now=1600).country
        self.assertEqual(bought.food, self.country.food + 100)
        self.assertEqual(
            bought.cash,
            self.country.cash - MARKET_PRICES["food"][0] * 100,
        )

        sold = sell_market(bought, good="food", amount=100, now=1600).country
        self.assertEqual(sold.food, self.country.food)
        self.assertGreater(sold.cash, bought.cash)

    def test_democracy_has_no_market_commission(self) -> None:
        democracy = replace(self.country, government="democracy")
        sold = sell_market(democracy, good="oil", amount=10, now=1600).country

        self.assertEqual(
            sold.cash,
            democracy.cash + MARKET_PRICES["oil"][1] * 10,
        )

    def test_standard_strike_captures_land(self) -> None:
        attacker = replace(
            self.country,
            troops=5000,
            tanks=800,
            jets=600,
            oil=2000,
        )
        defender = new_country(
            user_id=2,
            round_id=1,
            name="Soft Target",
            ruler="target",
            now=1000,
            rules=self.rules,
        )
        defender = replace(defender, id=2, troops=50, tanks=0, turrets=10)

        result = standard_strike(
            attacker,
            defender,
            now=1700,
            rules=self.rules,
            rng=Random(1),
        )

        self.assertGreater(result.attacker.land, attacker.land)
        self.assertLess(result.defender.land, defender.land)
        self.assertLess(result.attacker.turns, attacker.turns)
        self.assertLess(result.attacker.military_readiness, attacker.military_readiness)

    def test_spy_intel_spends_turns_and_reports_target(self) -> None:
        actor = replace(self.country, spies=1000)
        target = new_country(
            user_id=2,
            round_id=1,
            name="Hidden Valley",
            ruler="target",
            now=1000,
            rules=self.rules,
        )

        result = spy_intel(actor, target, now=1800, rng=Random(1))

        self.assertEqual(result.country.turns, actor.turns - 2)
        self.assertLess(result.country.spy_readiness, actor.spy_readiness)
        self.assertIn("Hidden Valley", result.message)

    def test_launch_cruise_missile_damages_units(self) -> None:
        attacker = replace(self.country, missiles_cruise=1)
        target = new_country(
            user_id=2,
            round_id=1,
            name="Missile Target",
            ruler="target",
            now=1000,
            rules=self.rules,
        )
        target = replace(target, troops=1000, jets=100, tanks=100, turrets=100)

        result = launch_missile(
            attacker,
            target,
            missile="cruise",
            now=1800,
            rng=Random(1),
        )

        self.assertEqual(result.attacker.missiles_cruise, 0)
        self.assertEqual(result.attacker.turns, attacker.turns - 2)
        self.assertLess(result.defender.troops, target.troops)

    def test_new_country_has_earthlike_state(self) -> None:
        self.assertEqual(self.country.government, "monarchy")
        self.assertEqual(self.country.tax_rate, 35)
        self.assertGreater(self.country.oil, 0)
        self.assertGreater(self.country.troops, 0)
        self.assertGreater(self.country.spies, 0)
        self.assertEqual(
            sum(
                [
                    self.country.industrial_troops,
                    self.country.industrial_jets,
                    self.country.industrial_tanks,
                    self.country.industrial_turrets,
                ]
            ),
            100,
        )

    def test_governments_include_earthlike_set(self) -> None:
        self.assertEqual(
            set(GOVERNMENTS),
            {
                "monarchy",
                "fascism",
                "tyranny",
                "dictatorship",
                "communism",
                "theocracy",
                "republic",
                "democracy",
            },
        )
        self.assertEqual(canonical_government("Republic"), "republic")

    def test_government_modifiers_are_applied(self) -> None:
        republic = replace(self.country, government="republic")
        tyranny = replace(self.country, government="tyranny")
        democracy = replace(self.country, government="democracy")

        self.assertGreater(government_for(republic).explore_gains, 1.0)
        self.assertEqual(government_for(tyranny).attack_turns, 1)
        self.assertEqual(government_for(democracy).market_commission, 0.0)

    def test_economy_pass_produces_core_resources(self) -> None:
        delta = economy_for_turns(self.country, 4, self.rules)

        self.assertGreater(delta.cash_income, 0)
        self.assertGreater(delta.food_produced, 0)
        self.assertGreater(delta.oil_produced, 0)
        self.assertGreaterEqual(delta.population_growth, 0)
        self.assertGreater(delta.troops_produced, 0)

    def test_apply_economy_updates_resources_and_units(self) -> None:
        country, delta = apply_economy(self.country, 4, now=1300, rules=self.rules)

        self.assertEqual(country.food, self.country.food + delta.food_delta)
        self.assertEqual(country.oil, self.country.oil + delta.oil_delta)
        self.assertEqual(country.troops, self.country.troops + delta.troops_produced)
        self.assertGreater(country.cash, self.country.cash)
