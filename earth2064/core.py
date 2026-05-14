from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil
from random import Random
from typing import Iterable


BUILDING_TYPES = {
    "farms",
    "industry",
    "labs",
    "residences",
    "bases",
    "defense",
}


@dataclass(frozen=True)
class GameRules:
    turn_interval_seconds: int = 300
    max_turns: int = 80
    initial_turns: int = 25
    starting_land: int = 100
    starting_population: int = 800
    starting_food: int = 1500
    starting_cash: int = 5000
    starting_farms: int = 20
    starting_industry: int = 10
    starting_residences: int = 10
    farms_per_build_turn: int = 5
    farm_cost: int = 120
    explore_min_land: int = 8
    explore_max_land: int = 14


@dataclass(frozen=True)
class Country:
    id: int | None
    user_id: int
    round_id: int
    name: str
    ruler: str
    created_at: int
    updated_at: int
    last_turn_at: int
    turns: int
    land: int
    population: int
    food: int
    cash: int
    technology: int
    farms: int
    industry: int
    labs: int
    residences: int
    bases: int
    defense: int
    construction: int = 0

    @property
    def used_land(self) -> int:
        return (
            self.farms
            + self.industry
            + self.labs
            + self.residences
            + self.bases
            + self.defense
            + self.construction
        )

    @property
    def free_land(self) -> int:
        return max(0, self.land - self.used_land)

    @property
    def networth(self) -> int:
        buildings = self.used_land
        return int(
            self.land * 55
            + self.population * 2
            + self.food * 0.15
            + self.cash * 0.08
            + buildings * 80
            + self.technology * 150
        )


@dataclass(frozen=True)
class EconomyDelta:
    turns: int
    food_produced: int
    food_consumed: int
    cash_income: int
    cash_expenses: int
    population_growth: int

    @property
    def food_delta(self) -> int:
        return self.food_produced - self.food_consumed

    @property
    def cash_delta(self) -> int:
        return self.cash_income - self.cash_expenses


@dataclass(frozen=True)
class ActionResult:
    country: Country
    message: str
    economy: EconomyDelta | None = None
    news: str | None = None


def new_country(
    *,
    user_id: int,
    round_id: int,
    name: str,
    ruler: str,
    now: int,
    rules: GameRules,
) -> Country:
    return Country(
        id=None,
        user_id=user_id,
        round_id=round_id,
        name=name,
        ruler=ruler,
        created_at=now,
        updated_at=now,
        last_turn_at=now,
        turns=rules.initial_turns,
        land=rules.starting_land,
        population=rules.starting_population,
        food=rules.starting_food,
        cash=rules.starting_cash,
        technology=0,
        farms=rules.starting_farms,
        industry=rules.starting_industry,
        labs=0,
        residences=rules.starting_residences,
        bases=0,
        defense=0,
        construction=0,
    )


def accrue_turns(
    country: Country,
    *,
    now: int,
    rules: GameRules,
) -> tuple[Country, int]:
    if country.turns >= rules.max_turns:
        return replace(country, last_turn_at=now, updated_at=now), 0

    elapsed = max(0, now - country.last_turn_at)
    possible = elapsed // rules.turn_interval_seconds
    if possible <= 0:
        return country, 0

    new_turns = min(rules.max_turns, country.turns + possible)
    gained = new_turns - country.turns
    if new_turns >= rules.max_turns:
        last_turn_at = now
    else:
        last_turn_at = country.last_turn_at + possible * rules.turn_interval_seconds

    return (
        replace(
            country,
            turns=new_turns,
            last_turn_at=last_turn_at,
            updated_at=now,
        ),
        gained,
    )


def economy_for_turns(country: Country, turns: int) -> EconomyDelta:
    food_produced = turns * (country.farms * 7 + max(1, country.land // 12))
    food_consumed = turns * max(1, country.population // 35)
    cash_income = turns * (country.population // 12 + country.industry * 35)
    cash_expenses = turns * max(1, country.used_land * 2 + country.population // 80)
    population_growth = turns * max(1, country.residences * 3 + country.land // 40)
    return EconomyDelta(
        turns=turns,
        food_produced=food_produced,
        food_consumed=food_consumed,
        cash_income=cash_income,
        cash_expenses=cash_expenses,
        population_growth=population_growth,
    )


def apply_economy(country: Country, turns: int, *, now: int) -> tuple[Country, EconomyDelta]:
    delta = economy_for_turns(country, turns)
    return (
        replace(
            country,
            food=max(0, country.food + delta.food_delta),
            cash=max(0, country.cash + delta.cash_delta),
            population=max(100, country.population + delta.population_growth),
            updated_at=now,
        ),
        delta,
    )


def require_turns(country: Country, turns: int) -> None:
    if turns <= 0:
        raise ValueError("Use at least 1 turn.")
    if country.turns < turns:
        raise ValueError(f"Need {turns} turns, have {country.turns}.")


def cash_action(country: Country, *, turns: int, now: int) -> ActionResult:
    require_turns(country, turns)
    country = replace(country, turns=country.turns - turns)
    country, economy = apply_economy(country, turns, now=now)
    return ActionResult(
        country=country,
        message=f"Worked {turns} turns for food and cash.",
        economy=economy,
    )


def explore(
    country: Country,
    *,
    turns: int,
    now: int,
    rules: GameRules,
    rng: Random,
) -> ActionResult:
    require_turns(country, turns)
    country = replace(country, turns=country.turns - turns)
    country, economy = apply_economy(country, turns, now=now)
    gained_land = sum(
        rng.randint(rules.explore_min_land, rules.explore_max_land)
        for _ in range(turns)
    )
    country = replace(country, land=country.land + gained_land, updated_at=now)
    news = f"{country.name} explored {gained_land} acres."
    return ActionResult(
        country=country,
        message=f"Explored {gained_land} acres.",
        economy=economy,
        news=news,
    )


def build(
    country: Country,
    *,
    building: str,
    amount: int,
    now: int,
    rules: GameRules,
) -> ActionResult:
    building = building.lower()
    if building not in BUILDING_TYPES:
        raise ValueError("Unknown building type.")
    if amount <= 0:
        raise ValueError("Build at least 1 building.")
    if building != "farms":
        raise ValueError("Prototype only supports FARMS.")
    if amount > country.free_land:
        raise ValueError(f"Only {country.free_land} free land.")

    turns = ceil(amount / rules.farms_per_build_turn)
    require_turns(country, turns)

    cost = amount * rules.farm_cost
    if country.cash < cost:
        raise ValueError(f"Need ${cost}, have ${country.cash}.")

    country = replace(country, turns=country.turns - turns)
    country, economy = apply_economy(country, turns, now=now)
    country = replace(
        country,
        cash=max(0, country.cash - cost),
        farms=country.farms + amount,
        updated_at=now,
    )
    news = f"{country.name} built {amount} farms."
    return ActionResult(
        country=country,
        message=f"Built {amount} farms for ${cost}.",
        economy=economy,
        news=news,
    )


def score_rows(countries: Iterable[Country]) -> list[Country]:
    return sorted(countries, key=lambda country: country.networth, reverse=True)
