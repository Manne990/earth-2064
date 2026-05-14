from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil
from random import Random
from typing import Iterable


@dataclass(frozen=True)
class Government:
    key: str
    label: str
    cash_income: float = 1.0
    food_production: float = 1.0
    oil_production: float = 1.0
    industrial_production: float = 1.0
    construction_speed: float = 1.0
    military_strength: float = 1.0
    spy_effectiveness: float = 1.0
    attack_gains: float = 1.0
    military_cost: float = 1.0
    market_commission: float = 0.08
    max_population: float = 1.0
    max_technology: float = 1.0
    explore_gains: float = 1.0
    attack_turns: int = 2


GOVERNMENTS: dict[str, Government] = {
    "monarchy": Government("monarchy", "Monarchy"),
    "fascism": Government(
        "fascism",
        "Fascism",
        food_production=1.15,
        oil_production=1.20,
        industrial_production=1.15,
        construction_speed=1.20,
        cash_income=0.85,
        max_population=0.80,
        market_commission=0.15,
    ),
    "tyranny": Government(
        "tyranny",
        "Tyranny",
        attack_gains=1.10,
        military_cost=0.90,
        cash_income=0.85,
        attack_turns=1,
    ),
    "dictatorship": Government(
        "dictatorship",
        "Dictatorship",
        military_strength=1.20,
        spy_effectiveness=1.25,
        construction_speed=0.70,
    ),
    "communism": Government(
        "communism",
        "Communism",
        industrial_production=1.25,
        max_technology=1.20,
        market_commission=0.10,
    ),
    "theocracy": Government(
        "theocracy",
        "Theocracy",
        construction_speed=1.40,
        military_cost=0.75,
        max_technology=0.65,
    ),
    "republic": Government(
        "republic",
        "Republic",
        cash_income=1.20,
        explore_gains=1.20,
        military_strength=0.85,
    ),
    "democracy": Government(
        "democracy",
        "Democracy",
        max_technology=1.10,
        market_commission=0.0,
        attack_turns=3,
    ),
}


@dataclass(frozen=True)
class BuildingSpec:
    key: str
    label: str
    cost: int
    aliases: tuple[str, ...]


BUILDINGS: dict[str, BuildingSpec] = {
    "enterprise": BuildingSpec(
        "enterprise",
        "Enterprise Zones",
        450,
        ("enterprise", "enterprises", "ez", "zones"),
    ),
    "residences": BuildingSpec(
        "residences",
        "Residences",
        300,
        ("residence", "residences", "res", "homes"),
    ),
    "industry": BuildingSpec(
        "industry",
        "Industrial Complexes",
        650,
        ("industry", "industrial", "ind", "complexes"),
    ),
    "bases": BuildingSpec(
        "bases",
        "Military Bases",
        500,
        ("base", "bases", "military"),
    ),
    "labs": BuildingSpec(
        "labs",
        "Research Labs",
        700,
        ("lab", "labs", "research"),
    ),
    "farms": BuildingSpec(
        "farms",
        "Farms",
        260,
        ("farm", "farms", "food"),
    ),
    "oil_rigs": BuildingSpec(
        "oil_rigs",
        "Oil Rigs",
        550,
        ("oil", "rig", "rigs", "oilrigs", "oil_rigs"),
    ),
    "construction": BuildingSpec(
        "construction",
        "Construction Sites",
        220,
        ("construction", "cs", "sites"),
    ),
}

BUILDING_ALIASES = {
    alias: key
    for key, spec in BUILDINGS.items()
    for alias in spec.aliases
}
BUILDING_TYPES = set(BUILDINGS)

TECH_TYPES = {
    "military",
    "medical",
    "business",
    "residential",
    "agricultural",
    "warfare",
    "weapons",
    "industrial",
    "spy",
    "sdi",
}

UNIT_TYPES = {"troops", "jets", "tanks", "turrets", "spies"}
MISSILE_TYPES = {"nuclear", "chemical", "cruise"}


@dataclass(frozen=True)
class GameRules:
    turn_interval_seconds: int = 300
    max_turns: int = 360
    initial_turns: int = 80
    starting_land: int = 100
    starting_population: int = 6000
    starting_food: int = 5000
    starting_cash: int = 20000
    starting_oil: int = 1000
    starting_enterprise: int = 10
    starting_residences: int = 20
    starting_industry: int = 15
    starting_bases: int = 5
    starting_labs: int = 5
    starting_farms: int = 20
    starting_oil_rigs: int = 5
    starting_construction: int = 10
    starting_troops: int = 120
    starting_jets: int = 20
    starting_tanks: int = 10
    starting_turrets: int = 30
    starting_spies: int = 25
    base_per_capita_income: float = 3.0
    enterprise_income_bonus: float = 0.02
    residence_capacity: int = 350
    food_per_farm: int = 35
    oil_per_rig: int = 4
    food_people_per_bushel: int = 20
    building_expense: int = 8
    industrial_points_per_complex: float = 2.4
    explore_min_land: int = 6
    explore_max_land: int = 12


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
    oil: int
    technology: int
    government: str
    tax_rate: int
    enterprise: int
    residences: int
    industry: int
    bases: int
    labs: int
    farms: int
    oil_rigs: int
    construction: int
    defense: int
    troops: int
    jets: int
    tanks: int
    turrets: int
    spies: int
    missiles_nuclear: int
    missiles_chemical: int
    missiles_cruise: int
    tech_military: int
    tech_medical: int
    tech_business: int
    tech_residential: int
    tech_agricultural: int
    tech_warfare: int
    tech_weapons: int
    tech_industrial: int
    tech_spy: int
    tech_sdi: int
    military_readiness: int
    spy_readiness: int
    industrial_troops: int
    industrial_jets: int
    industrial_tanks: int
    industrial_turrets: int

    @property
    def used_land(self) -> int:
        return (
            self.enterprise
            + self.residences
            + self.industry
            + self.bases
            + self.labs
            + self.farms
            + self.oil_rigs
            + self.construction
            + self.defense
        )

    @property
    def free_land(self) -> int:
        return max(0, self.land - self.used_land)

    @property
    def tech_total(self) -> int:
        return (
            self.technology
            + self.tech_military
            + self.tech_medical
            + self.tech_business
            + self.tech_residential
            + self.tech_agricultural
            + self.tech_warfare
            + self.tech_weapons
            + self.tech_industrial
            + self.tech_spy
            + self.tech_sdi
        )

    @property
    def networth(self) -> int:
        units = (
            self.troops * 0.6
            + self.jets * 3
            + self.tanks * 4
            + self.turrets * 2
            + self.spies * 2
        )
        missiles = (
            self.missiles_nuclear
            + self.missiles_chemical
            + self.missiles_cruise
        ) * 150
        return int(
            self.land * 45
            + self.population * 0.5
            + self.cash * 0.04
            + self.food * 0.05
            + self.oil * 0.1
            + self.used_land * 100
            + self.tech_total * 0.12
            + units
            + missiles
        )


@dataclass(frozen=True)
class EconomyDelta:
    turns: int
    food_produced: int
    food_consumed: int
    oil_produced: int
    oil_consumed: int
    cash_income: int
    cash_expenses: int
    population_growth: int
    troops_produced: int = 0
    jets_produced: int = 0
    tanks_produced: int = 0
    turrets_produced: int = 0

    @property
    def food_delta(self) -> int:
        return self.food_produced - self.food_consumed

    @property
    def oil_delta(self) -> int:
        return self.oil_produced - self.oil_consumed

    @property
    def cash_delta(self) -> int:
        return self.cash_income - self.cash_expenses


@dataclass(frozen=True)
class ActionResult:
    country: Country
    message: str
    economy: EconomyDelta | None = None
    news: str | None = None


@dataclass(frozen=True)
class ConflictResult:
    attacker: Country
    defender: Country
    message: str
    news: str | None = None


def canonical_government(government: str) -> str:
    key = government.lower().strip()
    if key not in GOVERNMENTS:
        raise ValueError("Unknown government.")
    return key


def government_for(country: Country) -> Government:
    return GOVERNMENTS.get(country.government, GOVERNMENTS["monarchy"])


def canonical_building(building: str) -> str:
    key = building.lower().strip().replace("-", "_")
    key = BUILDING_ALIASES.get(key, key)
    if key not in BUILDINGS:
        raise ValueError("Unknown building type.")
    return key


def canonical_tech(tech: str) -> str:
    key = tech.lower().strip().replace("-", "_")
    if key not in TECH_TYPES:
        raise ValueError("Unknown technology.")
    return key


def canonical_unit(unit: str) -> str:
    key = unit.lower().strip()
    if key not in UNIT_TYPES:
        raise ValueError("Unknown unit.")
    return key


def canonical_missile(missile: str) -> str:
    key = missile.lower().strip()
    if key not in MISSILE_TYPES:
        raise ValueError("Unknown missile.")
    return key


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
        oil=rules.starting_oil,
        technology=0,
        government="monarchy",
        tax_rate=35,
        enterprise=rules.starting_enterprise,
        residences=rules.starting_residences,
        industry=rules.starting_industry,
        bases=rules.starting_bases,
        labs=rules.starting_labs,
        farms=rules.starting_farms,
        oil_rigs=rules.starting_oil_rigs,
        construction=rules.starting_construction,
        defense=0,
        troops=rules.starting_troops,
        jets=rules.starting_jets,
        tanks=rules.starting_tanks,
        turrets=rules.starting_turrets,
        spies=rules.starting_spies,
        missiles_nuclear=0,
        missiles_chemical=0,
        missiles_cruise=0,
        tech_military=0,
        tech_medical=0,
        tech_business=0,
        tech_residential=0,
        tech_agricultural=0,
        tech_warfare=0,
        tech_weapons=0,
        tech_industrial=0,
        tech_spy=0,
        tech_sdi=0,
        military_readiness=100,
        spy_readiness=100,
        industrial_troops=50,
        industrial_jets=20,
        industrial_tanks=20,
        industrial_turrets=10,
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


def require_turns(country: Country, turns: int) -> None:
    if turns <= 0:
        raise ValueError("Use at least 1 turn.")
    if country.turns < turns:
        raise ValueError(f"Need {turns} turns, have {country.turns}.")


def tech_points(country: Country, tech: str) -> int:
    return int(getattr(country, f"tech_{canonical_tech(tech)}"))


def tech_bonus(country: Country, tech: str, *, cap: float = 0.75) -> float:
    points = tech_points(country, tech)
    gov = government_for(country)
    raw = min(cap * gov.max_technology, points / 10000)
    return 1.0 + raw


def population_capacity(country: Country, rules: GameRules) -> int:
    gov = government_for(country)
    tech = tech_bonus(country, "residential", cap=0.60)
    return int(country.residences * rules.residence_capacity * gov.max_population * tech)


def build_rate(country: Country) -> int:
    gov = government_for(country)
    return max(1, int((4 + country.construction // 8) * gov.construction_speed))


def military_upkeep(country: Country) -> int:
    gov = government_for(country)
    base = (
        country.troops * 0.06
        + country.jets * 0.35
        + country.tanks * 0.45
        + country.turrets * 0.12
        + country.spies * 0.20
    )
    base *= max(0.55, 1.0 - country.bases * 0.002)
    return int(base * gov.military_cost)


def production_for_turns(country: Country, turns: int, rules: GameRules) -> dict[str, int]:
    gov = government_for(country)
    pool = (
        country.industry
        * rules.industrial_points_per_complex
        * turns
        * gov.industrial_production
        * tech_bonus(country, "industrial", cap=0.50)
    )
    costs = {"troops": 1.0, "jets": 3.0, "tanks": 5.0, "turrets": 2.0}
    allocation = {
        "troops": country.industrial_troops,
        "jets": country.industrial_jets,
        "tanks": country.industrial_tanks,
        "turrets": country.industrial_turrets,
    }
    return {
        unit: int((pool * pct / 100) / costs[unit])
        for unit, pct in allocation.items()
    }


def economy_for_turns(
    country: Country,
    turns: int,
    rules: GameRules | None = None,
) -> EconomyDelta:
    rules = rules or GameRules()
    gov = government_for(country)
    business = tech_bonus(country, "business", cap=0.60)
    agricultural = tech_bonus(country, "agricultural", cap=0.75)
    medical = tech_bonus(country, "medical", cap=0.40)
    weapons = tech_bonus(country, "weapons", cap=0.40)
    per_capita = (
        rules.base_per_capita_income
        + country.enterprise * rules.enterprise_income_bonus
    ) * gov.cash_income * business
    cash_income = int(turns * country.population * per_capita * country.tax_rate / 100)
    food_produced = int(
        turns * country.farms * rules.food_per_farm * gov.food_production * agricultural
    )
    military_food = (
        country.troops // 50
        + country.jets // 30
        + country.tanks // 20
        + country.turrets // 40
    )
    food_consumed = turns * max(
        1,
        country.population // rules.food_people_per_bushel + military_food,
    )
    oil_produced = int(turns * country.oil_rigs * rules.oil_per_rig * gov.oil_production)
    cash_expenses = turns * (
        country.used_land * rules.building_expense
        + int(military_upkeep(country) * weapons)
    )
    cap = population_capacity(country, rules)
    pop_room = max(0, cap - country.population)
    population_growth = min(
        pop_room,
        int(turns * max(0, country.residences * 20) * medical),
    )
    produced = production_for_turns(country, turns, rules)
    return EconomyDelta(
        turns=turns,
        food_produced=food_produced,
        food_consumed=food_consumed,
        oil_produced=oil_produced,
        oil_consumed=0,
        cash_income=cash_income,
        cash_expenses=cash_expenses,
        population_growth=population_growth,
        troops_produced=produced["troops"],
        jets_produced=produced["jets"],
        tanks_produced=produced["tanks"],
        turrets_produced=produced["turrets"],
    )


def apply_economy(
    country: Country,
    turns: int,
    *,
    now: int,
    rules: GameRules | None = None,
) -> tuple[Country, EconomyDelta]:
    delta = economy_for_turns(country, turns, rules)
    return (
        replace(
            country,
            food=max(0, country.food + delta.food_delta),
            oil=max(0, country.oil + delta.oil_delta),
            cash=max(0, country.cash + delta.cash_delta),
            population=max(100, country.population + delta.population_growth),
            troops=country.troops + delta.troops_produced,
            jets=country.jets + delta.jets_produced,
            tanks=country.tanks + delta.tanks_produced,
            turrets=country.turrets + delta.turrets_produced,
            updated_at=now,
        ),
        delta,
    )


def cash_action(
    country: Country,
    *,
    turns: int,
    now: int,
    rules: GameRules | None = None,
) -> ActionResult:
    rules = rules or GameRules()
    require_turns(country, turns)
    country = replace(country, turns=country.turns - turns)
    country, economy = apply_economy(country, turns, now=now, rules=rules)
    gov = government_for(country)
    bonus_cash = int(
        turns
        * max(1, country.population // 6)
        * gov.cash_income
        * tech_bonus(country, "business", cap=0.60)
    )
    country = replace(country, cash=country.cash + bonus_cash, updated_at=now)
    return ActionResult(
        country=country,
        message=f"Generated ${bonus_cash} cash.",
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
    country, economy = apply_economy(country, turns, now=now, rules=rules)
    gov = government_for(country)
    gained_land = sum(
        int(rng.randint(rules.explore_min_land, rules.explore_max_land) * gov.explore_gains)
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
    building_key = canonical_building(building)
    if amount <= 0:
        raise ValueError("Build at least 1 building.")
    if amount > country.free_land:
        raise ValueError(f"Only {country.free_land} free land.")

    spec = BUILDINGS[building_key]
    turns = ceil(amount / build_rate(country))
    require_turns(country, turns)

    cost = amount * spec.cost
    if country.cash < cost:
        raise ValueError(f"Need ${cost}, have ${country.cash}.")

    country = replace(country, turns=country.turns - turns)
    country, economy = apply_economy(country, turns, now=now, rules=rules)
    country = replace(
        country,
        cash=max(0, country.cash - cost),
        **{building_key: getattr(country, building_key) + amount},
        updated_at=now,
    )
    news = f"{country.name} built {amount} {spec.label.lower()}."
    return ActionResult(
        country=country,
        message=f"Built {amount} {spec.label.lower()} for ${cost}.",
        economy=economy,
        news=news,
    )


def research(
    country: Country,
    *,
    tech: str,
    turns: int,
    now: int,
    rules: GameRules | None = None,
) -> ActionResult:
    rules = rules or GameRules()
    tech_key = canonical_tech(tech)
    require_turns(country, turns)
    country = replace(country, turns=country.turns - turns)
    country, economy = apply_economy(country, turns, now=now, rules=rules)
    gov = government_for(country)
    points = int(turns * max(1, country.labs * 10 + country.land // 80) * gov.max_technology)
    field = f"tech_{tech_key}"
    country = replace(country, **{field: getattr(country, field) + points}, updated_at=now)
    return ActionResult(
        country=country,
        message=f"Researched {tech_key} for {points} points.",
        economy=economy,
    )


def produce_action(
    country: Country,
    *,
    turns: int,
    now: int,
    rules: GameRules | None = None,
) -> ActionResult:
    rules = rules or GameRules()
    require_turns(country, turns)
    country = replace(country, turns=country.turns - turns)
    country, economy = apply_economy(country, turns, now=now, rules=rules)
    return ActionResult(
        country=country,
        message=f"Ran production for {turns} turns.",
        economy=economy,
    )


def set_industrial_allocation(
    country: Country,
    *,
    troops: int,
    jets: int,
    tanks: int,
    turrets: int,
    now: int,
) -> ActionResult:
    values = [troops, jets, tanks, turrets]
    if any(value < 0 for value in values):
        raise ValueError("Allocation cannot be negative.")
    if sum(values) != 100:
        raise ValueError("Allocation must total 100.")
    country = replace(
        country,
        industrial_troops=troops,
        industrial_jets=jets,
        industrial_tanks=tanks,
        industrial_turrets=turrets,
        updated_at=now,
    )
    return ActionResult(country=country, message="Industrial allocation updated.")


MARKET_PRICES = {
    "food": (3, 2),
    "oil": (25, 18),
    "troops": (120, 80),
    "jets": (850, 550),
    "tanks": (1200, 800),
    "turrets": (650, 400),
}


def canonical_good(good: str) -> str:
    key = good.lower().strip()
    if key in {"bushels", "grain"}:
        key = "food"
    if key in {"barrels", "energy"}:
        key = "oil"
    if key not in MARKET_PRICES:
        raise ValueError("Unknown market good.")
    return key


def buy_market(country: Country, *, good: str, amount: int, now: int) -> ActionResult:
    good_key = canonical_good(good)
    if amount <= 0:
        raise ValueError("Buy at least 1.")
    buy_price, _ = MARKET_PRICES[good_key]
    cost = amount * buy_price
    if country.cash < cost:
        raise ValueError(f"Need ${cost}, have ${country.cash}.")
    country = replace(
        country,
        cash=country.cash - cost,
        **{good_key: getattr(country, good_key) + amount},
        updated_at=now,
    )
    return ActionResult(country=country, message=f"Bought {amount} {good_key} for ${cost}.")


def sell_market(country: Country, *, good: str, amount: int, now: int) -> ActionResult:
    good_key = canonical_good(good)
    if amount <= 0:
        raise ValueError("Sell at least 1.")
    if getattr(country, good_key) < amount:
        raise ValueError(f"Not enough {good_key}.")
    _, sell_price = MARKET_PRICES[good_key]
    commission = government_for(country).market_commission
    revenue = int(amount * sell_price * (1.0 - commission))
    country = replace(
        country,
        cash=country.cash + revenue,
        **{good_key: getattr(country, good_key) - amount},
        updated_at=now,
    )
    return ActionResult(country=country, message=f"Sold {amount} {good_key} for ${revenue}.")


def attack_power(country: Country) -> float:
    gov = government_for(country)
    weapons = tech_bonus(country, "weapons", cap=0.60)
    raw = country.troops + country.jets * 2 + country.tanks * 4
    return raw * gov.military_strength * weapons * country.military_readiness / 100


def defense_power(country: Country) -> float:
    weapons = tech_bonus(country, "weapons", cap=0.60)
    raw = country.troops + country.tanks * 4 + country.turrets * 2
    return raw * weapons * max(50, country.military_readiness) / 100


def reduce_units(country: Country, pct: float) -> Country:
    return replace(
        country,
        troops=max(0, country.troops - int(country.troops * pct)),
        jets=max(0, country.jets - int(country.jets * pct)),
        tanks=max(0, country.tanks - int(country.tanks * pct)),
        turrets=max(0, country.turrets - int(country.turrets * pct)),
    )


def standard_strike(
    attacker: Country,
    defender: Country,
    *,
    now: int,
    rules: GameRules | None = None,
    rng: Random,
) -> ConflictResult:
    rules = rules or GameRules()
    gov = government_for(attacker)
    turns = gov.attack_turns
    require_turns(attacker, turns)
    if attacker.military_readiness < 50:
        raise ValueError("Military readiness too low.")
    oil_cost = max(1, attacker.jets // 80 + attacker.tanks // 40)
    if attacker.oil < oil_cost:
        raise ValueError(f"Need {oil_cost} oil.")

    attacker = replace(
        attacker,
        turns=attacker.turns - turns,
        oil=attacker.oil - oil_cost,
        military_readiness=max(0, attacker.military_readiness - 18),
    )
    attacker, _ = apply_economy(attacker, turns, now=now, rules=rules)
    roll_attack = attack_power(attacker) * rng.uniform(0.85, 1.15)
    roll_defense = defense_power(defender) * rng.uniform(0.85, 1.15)

    if roll_attack <= roll_defense:
        attacker = reduce_units(attacker, 0.05)
        defender = reduce_units(defender, 0.02)
        return ConflictResult(
            attacker=replace(attacker, updated_at=now),
            defender=replace(defender, updated_at=now),
            message="Standard strike failed.",
            news=f"{attacker.name} failed a standard strike against {defender.name}.",
        )

    land_gain = max(1, int(defender.land * rng.uniform(0.03, 0.07) * gov.attack_gains))
    land_gain = min(land_gain, max(1, defender.land - 1))
    cash_loot = min(defender.cash, max(0, int(defender.cash * 0.04)))
    food_loot = min(defender.food, max(0, int(defender.food * 0.04)))
    oil_loot = min(defender.oil, max(0, int(defender.oil * 0.04)))
    attacker = reduce_units(attacker, 0.03)
    defender = reduce_units(defender, 0.06)
    attacker = replace(
        attacker,
        land=attacker.land + land_gain,
        cash=attacker.cash + cash_loot,
        food=attacker.food + food_loot,
        oil=attacker.oil + oil_loot,
        updated_at=now,
    )
    defender = replace(
        defender,
        land=max(1, defender.land - land_gain),
        cash=max(0, defender.cash - cash_loot),
        food=max(0, defender.food - food_loot),
        oil=max(0, defender.oil - oil_loot),
        updated_at=now,
    )
    return ConflictResult(
        attacker=attacker,
        defender=defender,
        message=f"Standard strike captured {land_gain} acres.",
        news=f"{attacker.name} captured {land_gain} acres from {defender.name}.",
    )


def spy_intel(
    actor: Country,
    target: Country,
    *,
    now: int,
    rng: Random,
) -> ActionResult:
    require_turns(actor, 2)
    actor = replace(
        actor,
        turns=actor.turns - 2,
        spy_readiness=max(0, actor.spy_readiness - 8),
        updated_at=now,
    )
    actor_score = actor.spies * government_for(actor).spy_effectiveness * rng.uniform(0.8, 1.2)
    target_score = max(1, target.spies) * rng.uniform(0.8, 1.2)
    if actor_score < target_score:
        return ActionResult(actor, f"Spy operation failed against {target.name}.")
    message = (
        f"{target.name}: land {target.land}, cash ${target.cash}, "
        f"troops {target.troops}, tanks {target.tanks}."
    )
    return ActionResult(actor, message)


def launch_missile(
    attacker: Country,
    defender: Country,
    *,
    missile: str,
    now: int,
    rng: Random,
) -> ConflictResult:
    missile_key = canonical_missile(missile)
    field = f"missiles_{missile_key}"
    require_turns(attacker, 2)
    if getattr(attacker, field) <= 0:
        raise ValueError(f"No {missile_key} missiles.")
    attacker = replace(
        attacker,
        turns=attacker.turns - 2,
        **{field: getattr(attacker, field) - 1},
        updated_at=now,
    )
    sdi_chance = min(0.80, defender.tech_sdi / 10000)
    if rng.random() < sdi_chance:
        return ConflictResult(
            attacker=attacker,
            defender=replace(defender, updated_at=now),
            message="Missile intercepted by SDI.",
            news=f"{defender.name} intercepted a missile from {attacker.name}.",
        )
    if missile_key == "nuclear":
        lost = max(1, int(defender.land * 0.04))
        defender = replace(defender, land=max(1, defender.land - lost), updated_at=now)
        message = f"Nuclear missile destroyed {lost} acres."
    elif missile_key == "chemical":
        lost = max(50, int(defender.population * 0.08))
        defender = replace(
            defender,
            population=max(100, defender.population - lost),
            updated_at=now,
        )
        message = f"Chemical missile killed {lost} civilians."
    else:
        defender = replace(
            defender,
            troops=max(0, defender.troops - int(defender.troops * 0.08)),
            jets=max(0, defender.jets - int(defender.jets * 0.08)),
            tanks=max(0, defender.tanks - int(defender.tanks * 0.08)),
            turrets=max(0, defender.turrets - int(defender.turrets * 0.08)),
            updated_at=now,
        )
        message = "Cruise missile damaged enemy forces."
    return ConflictResult(
        attacker=attacker,
        defender=defender,
        message=message,
        news=f"{attacker.name} launched a {missile_key} missile at {defender.name}.",
    )


def score_rows(countries: Iterable[Country]) -> list[Country]:
    return sorted(countries, key=lambda country: country.networth, reverse=True)
