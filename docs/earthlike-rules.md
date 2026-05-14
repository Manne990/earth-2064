# Earth 2064 Earth-Like Rules Spec

Earth 2064 aims to feel mechanically close to classic Earth-style browser
nation games while keeping its own fiction, wording, interface, and balance.
The target is not a byte-for-byte recreation. It is a compatible strategic
shape: turns, land, buildings, tech, market pressure, military readiness, and
round-based grudges.

Public references used as inspiration:

- Earth: 2025 player guides on GameFAQs for governments, buildings, units,
  attacks, technology, spying, and alliances.
- Earth Empires Wiki for the modern descendant shape of turns, countries,
  governments, and server rules.

Do not copy original game text into the product UI. Keep formulas in this file
as Earth 2064 approximations unless a future source audit confirms exact public
domain or licensed values.

## Core Loop

Players own one country per round. A country accumulates turns over time up to a
cap. Most actions spend turns. Spending turns also advances the country's
economy: population changes, taxes arrive, food and oil are produced, expenses
are paid, and industrial complexes produce military units.

The early loop should be:

```text
create country
explore land
build land
cash / produce / research
buy or sell on market
attack for land
read news and scores
repeat until round reset
```

## Country State

Required country resources:

```text
turns
land
population
cash
food
oil
military readiness
spy readiness
tax rate
industrial allocation
```

Required buildings:

```text
enterprise zones
residences
industrial complexes
military bases
research labs
farms
oil rigs
construction sites
```

Required units:

```text
troops
jets
tanks
turrets
spies
```

Required missiles:

```text
nuclear
chemical
cruise
```

Required tech fields:

```text
military
medical
business
residential
agricultural
warfare
weapons
industrial
spy
sdi
```

## Governments

The first Earth-like ruleset includes:

```text
monarchy
fascism
tyranny
dictatorship
communism
theocracy
republic
democracy
```

Governments are data-driven multipliers over economy, construction, attacks,
spies, market commission, and attack turn cost. The prototype starts every new
country as monarchy and exposes government as state so later commands can add
government switching penalties.

## Economy

Every spent turn should run a common economy pass:

```text
cash income      = population * per-capita income * tax rate
food production  = farms * agriculture effects
food consumption = population + military upkeep
oil production   = oil rigs * oil effects
cash expenses    = buildings + military upkeep
population grow  = residences, residential tech, medical tech, population cap
industry output  = industrial complexes, industrial tech, allocation
```

The exact constants are Earth 2064 balance values, not asserted original Earth
2025 constants.

## Actions

Minimum action set for the next server prototype:

```text
STATUS
EXPLORE turns
BUILD type amount
CASH turns
RESEARCH tech turns
PRODUCE turns
ALLOC troops jets tanks turrets
MARKET
BUY good amount
SELL good amount
ATTACK id STANDARD
SPY id INTEL
MISSILE id type
ALLY id
SCORES
NEWS
```

All terminal output must stay readable in 40 columns and plain ASCII.

## Implementation Plan

1. Write this rules spec and keep it updated as the prototype changes.
2. Expand the country model and SQLite persistence to Earth-like state.
3. Add governments as data-driven modifiers.
4. Replace the simple production function with a shared per-turn economy pass.
5. Implement Earth-like building types and construction-site build speed.
6. Add the technology model and a `RESEARCH` action.
7. Add industrial military production and allocation.
8. Add a first fixed-price market skeleton.
9. Add a first `STANDARD` landgrab attack.
10. Add foundations for spy intel, missiles, and alliances.

Each implementation step should include or update unit tests and run the full
test suite before moving to the next step.
