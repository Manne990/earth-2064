# Earch 2064

**Earch 2064** is a persistent, text-first strategy game inspired by classic
browser nation games such as Earth 2025, but designed from the start to be
playable from both retro computers and modern systems.

The goal is not to recreate Earth 2025 exactly. Earch 2064 should be its own
game: familiar in spirit, simple to access, easy to read in 40 columns, and
deep enough to support long-running multiplayer rounds, diplomacy, trade,
conflict, and community.

## Core Idea

Earch 2064 is a post-collapse country strategy game.

Each player controls a small country trying to survive and grow in a damaged
future world. Players manage land, population, food, money, buildings,
technology, military forces, diplomacy, and attacks.

The game is turn-based / tick-based. Players accumulate turns over time and
spend them on actions such as exploring land, building infrastructure,
producing resources, researching technology, spying, trading, or attacking
other countries.

## Design Goals

- Playable from a Commodore 64 Ultimate.
- Playable from other 8-bit and 16-bit retro computers.
- Playable from modern terminals and browsers.
- Text-first, with no required graphics.
- Plain ASCII baseline.
- 40-column layout as the primary compatibility target.
- Optional richer modes later: ANSI, PETSCII, VT100, 80-column, web UI.
- Server-authoritative game logic.
- Thin clients.
- Rounds/resets so new players can join without being permanently behind.
- Inspired by Earth 2025, but legally and creatively distinct.

## Target Platforms

The first version should work anywhere that can open a telnet-like text
session.

Primary target:

- Commodore 64 Ultimate / Ultimate64

Other intended retro targets:

- Commodore 64 with WiFi modem or compatible terminal setup
- Amiga
- Atari ST / STE / TT / Falcon
- Apple IIe / IIgs with networking hardware
- MSX / MSX2
- DOS PCs
- Classic Macintosh
- Atari 8-bit with FujiNet or similar
- Other terminal-capable retro systems

Modern targets:

- macOS / Linux / Windows terminal
- Web browser
- Possibly mobile browser later

## Why Text First?

A text-first interface makes the game accessible to old and new machines at the
same time.

A C64 player, an Amiga player, and a modern browser player should all be able
to participate in the same game world. Since Earch 2064 is turn-based and
strategic rather than reflex-based, no platform should have a major mechanical
advantage.

The lowest common denominator should be pleasant, not an afterthought.

Baseline terminal constraints:

```text
40 columns
plain ASCII
short lines
numbered menus
line-based input
no required ANSI escape codes
```

Example:

```text
EARCH 2064

1 COUNTRY
2 BUILD
3 EXPLORE
4 MARKET
5 MILITARY
6 ATTACK
7 NEWS
8 SCORES

> _
```

## Architecture

Earch 2064 should be built in layers.

```text
Game Core
  Pure game rules and simulation logic.
  No UI code.
  Easy to test.

Server
  Accounts, sessions, rounds, persistence.
  Runs ticks / turn generation.
  Exposes terminal and web/API interfaces.

Clients
  Terminal/telnet UI.
  Modern web UI.
  Optional native retro clients later.
```

## Version 1 Strategy

The first version should not include a custom native C64 client.

Instead, the first version should expose a telnet-like terminal interface. This
allows the game to be played from:

- C64 Ultimate terminal software
- WiFi modem terminal programs
- Amiga telnet clients
- Atari ST telnet clients
- DOS telnet clients
- Modern terminal programs

A native C64 client can come later if the protocol and game prove fun.

## Possible Future Native C64 Client

A native client may become useful later for:

- PETSCII UI
- custom frames and layout
- saved server/login settings
- faster navigation
- function-key shortcuts
- local rendering of status screens
- sound or music
- a more authentic C64 feel
- compact binary protocol support

This is explicitly not required for the first playable version.

## Core Game Concepts

Each country may have:

```text
name
ruler/player
government type
land
population
food
cash
oil/energy
technology
networth
turns
buildings
military
spies
messages
news
```

Initial building types may include:

```text
farms
industry
labs
residences
military bases
defense systems
construction sites
```

Initial military units may include:

```text
troops
jets
turrets
tanks
spies
```

The exact names can change. The important thing is that the model is simple
enough to understand from a terminal, but rich enough to create tradeoffs.

## Core Actions

First playable actions:

```text
create country
view country status
explore land
build buildings
cash / produce income
research technology
buy and sell goods
train military
attack another country
send messages
view scores
view news
```

## Turns and Ticks

The game should use accumulated turns.

Example model:

```text
players receive 1 turn every N minutes
turns accumulate up to a cap
most major actions spend turns
each turn updates production, consumption, expenses, and population
```

This works well for asynchronous play and retro systems.

## Rounds

The game should be round-based.

A round has a start date, end date, and scoreboard. At the end of a round,
winners are recorded and a new round begins.

This prevents the game from becoming permanently dominated by early players and
gives the community regular fresh starts.

Possible round lengths:

```text
fast test round: 1 week
normal round: 4-8 weeks
special event round: weekend
```

## Community Features

Earch 2064 should also be a meeting place for retro-computing players.

Possible community features:

```text
in-game messages
public news feed
alliances/clans
scoreboard
round history
platform badges
connection guides
```

Fun optional scoreboards:

```text
TOP COUNTRIES
TOP C64 COUNTRIES
TOP AMIGA COUNTRIES
TOP ATARI COUNTRIES
TOP TERMINAL COUNTRIES
```

Platform badges should be cosmetic only.

## Terminal Modes

The server should eventually support multiple display modes.

Initial mode:

```text
plain
```

Future modes:

```text
ansi
petscii
vt100
80col
web
```

The plain mode must always remain supported.

## Protocol Direction

The first terminal interface can be menu-based and human-readable.

Example commands:

```text
LOGIN username password
STATUS
BUILD FARM 10
EXPLORE 5
MARKET
ATTACK 1234 STANDARD 20
SCORES
NEWS
QUIT
```

The server can start with menus and later allow direct commands for faster
play.

## Relationship to Earth 2025

Earch 2064 is inspired by the feeling of Earth 2025 and similar old browser
strategy games.

However:

- It should not use the Earth 2025 name.
- It should not copy original text.
- It should not attempt to be a perfect clone.
- It should use its own rules, naming, balance, and fiction.

Useful public references include Earth Empires documentation and old player
guides, but Earch 2064 should become its own design.

## Research Notes

Earth 2025 original source code does not appear to be publicly available.

Earth Empires appears to have initially cloned many Earth 2025 mechanics and
formulas, but later evolved separately. Its public wiki includes useful formula
references for understanding the style of game economy.

Useful reference:

- Earth Empires Wiki
- Earth Empires Game Formulas
- old Earth 2025 guides via archived pages
- player memories and forum posts

These should be used as inspiration, not copied blindly.

## First Milestone

The first milestone should be a local playable prototype.

Required:

```text
server starts locally
SQLite database
create account
create country
login via terminal
view country status
accumulate turns
explore land
build farms
produce food/cash
view scoreboard
```

Nice to have:

```text
simple news feed
basic attacks
basic market
web status page
```

## Local Prototype

The repository now contains a small Python server prototype using only the
standard library:

```text
Game core     earch2064/core.py
SQLite store  earch2064/db.py
TCP server    earch2064/server.py
Web status    earch2064/web.py
```

Start it locally:

```sh
python3 -m earch2064 --db var/earch2064.sqlite --turn-seconds 60
```

Connect with a line terminal:

```sh
nc 127.0.0.1 2064
```

Useful first commands:

```text
REGISTER demo swordfish
COUNTRY North Demo
STATUS
EXPLORE 3
BUILD FARMS 10
CASH 5
SCORES
NEWS
QUIT
```

The optional web status page runs at:

```text
http://127.0.0.1:8080
```

Run the current tests:

```sh
python3 -m unittest discover
```

## Technical Preferences

A good initial stack could be:

```text
Python
FastAPI or plain asyncio server
SQLite
pytest
```

Possible network interfaces:

```text
HTTP API for web/dev tools
TCP line protocol for terminal/telnet clients
```

The game core should be independent from the network layer so it can be tested
without running a server.

## Project Spirit

Earch 2064 should feel like a game from an alternate timeline where 80s and 90s
machines never stopped talking to each other.

It should be simple enough to play from a C64, but interesting enough that
players on modern systems still care.

The dream:

```text
one persistent strategy world
many old machines
short commands
long grudges
fresh rounds
retro diplomacy
```
