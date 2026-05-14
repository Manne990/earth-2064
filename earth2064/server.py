from __future__ import annotations

import argparse
import asyncio
import signal
from dataclasses import dataclass
from pathlib import Path
from random import Random

from . import db
from .core import (
    MARKET_PRICES,
    GameRules,
    accrue_turns,
    build,
    buy_market,
    cash_action,
    explore,
    launch_missile,
    produce_action,
    research,
    score_rows,
    sell_market,
    set_industrial_allocation,
    spy_intel,
    standard_strike,
)
from .web import start_http_server


WIDTH = 40

MAIN_MENU = (
    ("1", "ADVISOR"),
    ("2", "BUILD"),
    ("3", "CASH"),
    ("4", "EXPLORE"),
    ("5", "MARKET"),
    ("6", "RESEARCH"),
    ("7", "MILITARY"),
    ("8", "WAR ROOM"),
    ("9", "NEWS"),
    ("0", "SCORES"),
)

BUILD_MENU = (
    ("1", "farms", "FARMS"),
    ("2", "enterprise", "ENTERPRISE"),
    ("3", "residences", "RESIDENCES"),
    ("4", "industry", "INDUSTRY"),
    ("5", "labs", "LABS"),
    ("6", "bases", "BASES"),
    ("7", "oil_rigs", "OIL RIGS"),
    ("8", "construction", "CONSTRUCTION"),
)

TECH_MENU = (
    ("1", "business", "BUSINESS"),
    ("2", "military", "MILITARY"),
    ("3", "medical", "MEDICAL"),
    ("4", "residential", "RESIDENTIAL"),
    ("5", "agricultural", "AGRICULTURAL"),
    ("6", "industrial", "INDUSTRIAL"),
    ("7", "weapons", "WEAPONS"),
    ("8", "warfare", "WARFARE"),
    ("9", "spy", "SPY"),
    ("0", "sdi", "SDI"),
)

MARKET_MENU = (
    ("1", "BUY", "food", "BUY FOOD"),
    ("2", "SELL", "food", "SELL FOOD"),
    ("3", "BUY", "oil", "BUY OIL"),
    ("4", "SELL", "oil", "SELL OIL"),
    ("5", "BUY", "troops", "BUY TROOPS"),
    ("6", "SELL", "troops", "SELL TROOPS"),
)


@dataclass
class ServerConfig:
    db_path: str
    host: str = "127.0.0.1"
    port: int = 2064
    http_host: str = "127.0.0.1"
    http_port: int | None = 8080
    turn_seconds: int = 300


def wrap_line(text: str, width: int = WIDTH) -> list[str]:
    if len(text) <= width:
        return [text]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if not current:
            current = word[:width]
        elif len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word[:width]
    if current:
        lines.append(current)
    return lines


def strip_telnet(data: bytes) -> str:
    out = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        if byte == 255:
            i += 1
            if i >= len(data):
                break
            command = data[i]
            i += 1
            if command == 250:
                while i < len(data) - 1:
                    if data[i] == 255 and data[i + 1] == 240:
                        i += 2
                        break
                    i += 1
            elif command in {251, 252, 253, 254}:
                i += 1
            continue
        if byte in {9, 10, 13} or 32 <= byte <= 126:
            out.append(byte)
        i += 1
    return out.decode("ascii", errors="ignore").strip()


def menu_choice(menu: tuple[tuple[str, ...], ...], choice: str) -> tuple[str, ...] | None:
    for item in menu:
        if item[0] == choice:
            return item
    return None


class TerminalSession:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        config: ServerConfig,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.config = config
        self.rules = GameRules(turn_interval_seconds=config.turn_seconds)
        self.conn = db.connect(config.db_path)
        db.initialize(self.conn)
        self.user = None
        self.country = None
        self.rng = Random()
        self.pending_input = bytearray()
        self.menu = "main"

    async def run(self) -> None:
        peer = self.writer.get_extra_info("peername")
        await self.send("")
        await self.send("EARTH 2064")
        await self.send("LOCAL SERVER PROTOTYPE")
        await self.send("")
        await self.send("Type HELP.")
        await self.send("")
        try:
            while True:
                await self.prompt()
                line = await self.read_command()
                if line is None:
                    break
                if not line:
                    continue
                keep_going = await self.handle(line)
                if not keep_going:
                    break
        finally:
            self.conn.close()
            self.writer.close()
            await self.writer.wait_closed()
            _ = peer

    async def read_command(self) -> str | None:
        data = bytearray()
        while len(data) < 160:
            chunk = await self.read_byte()
            if not chunk:
                return None if not data else strip_telnet(bytes(data))
            byte = chunk[0]
            if byte in {10, 13}:
                if byte == 13:
                    await self.consume_optional_lf()
                return strip_telnet(bytes(data))
            data.append(byte)
        return strip_telnet(bytes(data))

    async def read_byte(self) -> bytes:
        pending = getattr(self, "pending_input", bytearray())
        if pending:
            byte = bytes([pending.pop(0)])
            self.pending_input = pending
            return byte
        return await self.reader.read(1)

    async def consume_optional_lf(self) -> None:
        try:
            next_byte = await asyncio.wait_for(self.reader.read(1), timeout=0.01)
        except TimeoutError:
            return
        if next_byte and next_byte != b"\n":
            pending = getattr(self, "pending_input", bytearray())
            pending.extend(next_byte)
            self.pending_input = pending

    async def send(self, text: str = "") -> None:
        for line in wrap_line(text):
            self.writer.write((line + "\r\n").encode("ascii", errors="replace"))
        await self.writer.drain()

    async def prompt(self) -> None:
        self.writer.write(b"> ")
        await self.writer.drain()

    async def section(self, title: str) -> None:
        await self.send("")
        await self.send(title[:WIDTH])
        await self.send("-" * min(WIDTH, len(title)))

    async def handle(self, line: str) -> bool:
        parts = line.split()
        command = parts[0].upper()
        args = parts[1:]

        try:
            if command in {"QUIT", "EXIT", "Q"}:
                await self.send("Goodbye.")
                return False
            if command in {"MENU", "MAIN"}:
                await self.show_main_menu()
            elif await self.handle_menu_input(line):
                return True
            elif command == "HELP":
                await self.show_help()
            elif command == "REGISTER":
                await self.register(args)
            elif command == "LOGIN":
                await self.login(args)
            elif command == "COUNTRY":
                await self.create_country(" ".join(args))
            elif command == "STATUS" or command == "1":
                await self.show_status()
            elif command == "EXPLORE" or command == "2":
                await self.do_explore(args)
            elif command == "BUILD" or command == "3":
                if args:
                    await self.do_build(args)
                else:
                    await self.show_build_menu()
            elif command == "CASH" or command == "4":
                await self.do_cash(args)
            elif command == "SCORES" or command == "5":
                await self.show_scores()
            elif command == "NEWS" or command == "6":
                await self.show_news()
            elif command == "RESEARCH" or command == "RES":
                await self.do_research(args)
            elif command in {"PRODUCE", "PROD"}:
                await self.do_produce(args)
            elif command == "ALLOC":
                await self.do_alloc(args)
            elif command == "MARKET":
                await self.show_market_menu()
            elif command == "BUY":
                await self.do_buy(args)
            elif command == "SELL":
                await self.do_sell(args)
            elif command == "ATTACK":
                await self.do_attack(args)
            elif command == "SPY":
                await self.do_spy(args)
            elif command == "MISSILE":
                await self.do_missile(args)
            elif command == "ALLY":
                await self.do_ally(args)
            else:
                await self.send("Unknown command. Type HELP.")
        except ValueError as exc:
            await self.send(f"ERR {exc}")
        return True

    async def handle_menu_input(self, line: str) -> bool:
        if self.user is None or self.country is None:
            return False
        parts = line.split()
        if not parts:
            return True
        choice = parts[0].upper()
        args = parts[1:]

        if choice in {"B", "BACK", "M", "MENU"}:
            await self.show_main_menu()
            return True

        if self.menu == "main" and choice in {item[0] for item in MAIN_MENU}:
            await self.handle_main_choice(choice)
            return True
        if self.menu == "build" and choice in {item[0] for item in BUILD_MENU}:
            item = menu_choice(BUILD_MENU, choice)
            if item is None:
                return False
            if len(args) != 1:
                raise ValueError(f"Usage: {choice} amount")
            await self.do_build([item[1], args[0]])
            await self.show_build_menu()
            return True
        if self.menu == "cash" and choice.isdigit():
            await self.do_cash([choice])
            await self.show_cash_menu()
            return True
        if self.menu == "explore" and choice.isdigit():
            await self.do_explore([choice])
            await self.show_explore_menu()
            return True
        if self.menu == "research" and choice in {item[0] for item in TECH_MENU}:
            item = menu_choice(TECH_MENU, choice)
            if item is None:
                return False
            if len(args) != 1:
                raise ValueError(f"Usage: {choice} turns")
            await self.do_research([item[1], args[0]])
            await self.show_research_menu()
            return True
        if self.menu == "market" and choice in {item[0] for item in MARKET_MENU}:
            item = menu_choice(MARKET_MENU, choice)
            if item is None:
                return False
            if len(args) != 1:
                raise ValueError(f"Usage: {choice} amount")
            if item[1] == "BUY":
                await self.do_buy([item[2], args[0]])
            else:
                await self.do_sell([item[2], args[0]])
            await self.show_market_menu()
            return True
        if self.menu == "military":
            if choice == "1":
                if len(args) != 1:
                    raise ValueError("Usage: 1 turns")
                await self.do_produce([args[0]])
                await self.show_military_menu()
                return True
            if choice == "2":
                if len(args) != 4:
                    raise ValueError("Usage: 2 troops jets tanks turrets")
                await self.do_alloc(args)
                await self.show_military_menu()
                return True
            if choice == "3":
                await self.show_status()
                await self.show_military_menu()
                return True
        if self.menu == "war":
            if choice == "1":
                if len(args) != 1:
                    raise ValueError("Usage: 1 country_id")
                await self.do_attack([args[0], "STANDARD"])
                await self.show_war_menu()
                return True
            if choice == "2":
                if len(args) != 1:
                    raise ValueError("Usage: 2 country_id")
                await self.do_spy([args[0], "INTEL"])
                await self.show_war_menu()
                return True
            if choice == "3":
                if len(args) != 2:
                    raise ValueError("Usage: 3 country_id type")
                await self.do_missile(args)
                await self.show_war_menu()
                return True
            if choice == "4":
                if len(args) != 1:
                    raise ValueError("Usage: 4 country_id")
                await self.do_ally(args)
                await self.show_war_menu()
                return True
        return False

    async def handle_main_choice(self, choice: str) -> None:
        if choice == "1":
            await self.show_status()
        elif choice == "2":
            await self.show_build_menu()
        elif choice == "3":
            await self.show_cash_menu()
        elif choice == "4":
            await self.show_explore_menu()
        elif choice == "5":
            await self.show_market_menu()
        elif choice == "6":
            await self.show_research_menu()
        elif choice == "7":
            await self.show_military_menu()
        elif choice == "8":
            await self.show_war_menu()
        elif choice == "9":
            await self.show_news()
        elif choice == "0":
            await self.show_scores()

    async def show_help(self) -> None:
        await self.section("COMMANDS")
        if self.user is None:
            await self.send("REGISTER user pass")
            await self.send("LOGIN user pass")
            await self.send("SCORES")
            await self.send("NEWS")
            await self.send("QUIT")
            return
        if self.country is None:
            await self.send("COUNTRY name")
            await self.send("SCORES")
            await self.send("NEWS")
            await self.send("QUIT")
            return
        await self.send("MENU")
        await self.send("Numbers choose menu items.")
        await self.send("RESEARCH tech turns")
        await self.send("PRODUCE turns")
        await self.send("ALLOC tr jet tank tur")
        await self.send("MARKET / BUY / SELL")
        await self.send("ATTACK id STANDARD")
        await self.send("SPY id INTEL")
        await self.send("MISSILE id type")
        await self.send("ALLY id")
        await self.send("QUIT")
        await self.show_main_menu()

    async def show_main_menu(self) -> None:
        self.menu = "main"
        await self.section("EARTH 2064")
        for number, label in MAIN_MENU:
            await self.send(f"{number} {label}")
        await self.send("B BACK  Q QUIT")

    async def show_build_menu(self) -> None:
        await self.refresh_country()
        country = self.require_country()
        self.menu = "build"
        await self.section("BUILD")
        await self.send(f"Free land: {country.free_land}")
        await self.send(f"Turns: {country.turns}")
        for number, _key, label in BUILD_MENU:
            await self.send(f"{number} {label}")
        await self.send("Type: number amount")
        await self.send("B BACK")

    async def show_cash_menu(self) -> None:
        await self.refresh_country()
        country = self.require_country()
        self.menu = "cash"
        await self.section("CASH")
        await self.send(f"Turns: {country.turns}")
        await self.send("Type turns to work.")
        await self.send("Example: 10")
        await self.send("B BACK")

    async def show_explore_menu(self) -> None:
        await self.refresh_country()
        country = self.require_country()
        self.menu = "explore"
        await self.section("EXPLORE")
        await self.send(f"Land: {country.land}")
        await self.send(f"Turns: {country.turns}")
        await self.send("Type turns to explore.")
        await self.send("Example: 5")
        await self.send("B BACK")

    async def show_research_menu(self) -> None:
        await self.refresh_country()
        country = self.require_country()
        self.menu = "research"
        await self.section("RESEARCH")
        await self.send(f"Labs: {country.labs}")
        await self.send(f"Turns: {country.turns}")
        for number, _key, label in TECH_MENU:
            await self.send(f"{number} {label}")
        await self.send("Type: number turns")
        await self.send("B BACK")

    async def show_market_menu(self) -> None:
        self.menu = "market"
        await self.section("MARKET")
        await self.send("GOOD BUY SELL")
        for good, (buy, sell) in MARKET_PRICES.items():
            await self.send(f"{good[:7]:<7} {buy:<4} {sell:<4}")
        for number, _action, _good, label in MARKET_MENU:
            await self.send(f"{number} {label}")
        await self.send("Type: number amount")
        await self.send("B BACK")

    async def show_military_menu(self) -> None:
        await self.refresh_country()
        country = self.require_country()
        self.menu = "military"
        await self.section("MILITARY")
        await self.send(f"Turns: {country.turns}")
        await self.send(f"Troops/Jets: {country.troops}/{country.jets}")
        await self.send(f"Tanks/Turrets: {country.tanks}/{country.turrets}")
        await self.send(
            "Alloc: "
            f"{country.industrial_troops}/"
            f"{country.industrial_jets}/"
            f"{country.industrial_tanks}/"
            f"{country.industrial_turrets}"
        )
        await self.send("1 PRODUCE turns")
        await self.send("2 ALLOC tr jet tank tur")
        await self.send("3 ADVISOR")
        await self.send("B BACK")

    async def show_war_menu(self) -> None:
        self.menu = "war"
        await self.section("WAR ROOM")
        await self.send("Targets:")
        countries = score_rows(db.list_countries(self.conn))[:6]
        for country in countries:
            await self.send(f"#{country.id} {country.name[:18]}")
        await self.send("1 ATTACK id")
        await self.send("2 SPY id")
        await self.send("3 MISSILE id type")
        await self.send("4 ALLY id")
        await self.send("B BACK")

    async def register(self, args: list[str]) -> None:
        if len(args) != 2:
            raise ValueError("Usage: REGISTER user pass")
        user_id = db.create_user(self.conn, args[0], args[1])
        self.user = self.conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        self.country = db.get_country_for_user(self.conn, user_id=user_id)
        await self.send("Account created and logged in.")
        await self.send("Create country: COUNTRY name")

    async def login(self, args: list[str]) -> None:
        if len(args) != 2:
            raise ValueError("Usage: LOGIN user pass")
        self.user = db.authenticate(self.conn, args[0], args[1])
        self.country = db.get_country_for_user(self.conn, user_id=int(self.user["id"]))
        await self.send(f"Logged in as {self.user['username']}.")
        if self.country is None:
            await self.send("Create country: COUNTRY name")
        else:
            await self.refresh_country()
            await self.show_status()
            await self.show_main_menu()

    async def create_country(self, name: str) -> None:
        if self.user is None:
            raise ValueError("Login first.")
        if not name:
            raise ValueError("Usage: COUNTRY name")
        self.country = db.create_country(
            self.conn,
            user_id=int(self.user["id"]),
            ruler=str(self.user["username"]),
            name=name,
            rules=self.rules,
        )
        db.add_news(
            self.conn,
            round_id=self.country.round_id,
            text=f"{self.country.name} has entered the world.",
        )
        await self.send(f"Country created: {self.country.name}")
        await self.show_status()
        await self.show_main_menu()

    async def refresh_country(self) -> None:
        if self.user is None:
            return
        country = db.get_country_for_user(self.conn, user_id=int(self.user["id"]))
        if country is None:
            self.country = None
            return
        accrued, gained = accrue_turns(
            country,
            now=db.now_ts(),
            rules=self.rules,
        )
        self.country = accrued
        if gained:
            db.save_country(self.conn, accrued)

    def require_country(self):
        if self.user is None:
            raise ValueError("Login first.")
        if self.country is None:
            raise ValueError("Create a country first.")
        return self.country

    async def show_status(self) -> None:
        await self.refresh_country()
        country = self.require_country()
        await self.section("COUNTRY STATUS")
        await self.send(f"{country.name} #{country.id}")
        await self.send(f"Ruler: {country.ruler}")
        await self.send(f"Gov: {country.government}")
        await self.send(f"Turns: {country.turns}/{self.rules.max_turns}")
        await self.send(f"Land: {country.land} acres")
        await self.send(f"Free land: {country.free_land}")
        await self.send(f"Population: {country.population}")
        await self.send(f"Food: {country.food}")
        await self.send(f"Oil: {country.oil}")
        await self.send(f"Cash: ${country.cash}")
        await self.send(f"Tax: {country.tax_rate}%")
        await self.send(f"Farms: {country.farms}")
        await self.send(f"Industry: {country.industry}")
        await self.send(f"Labs: {country.labs}")
        await self.send(f"Troops: {country.troops}")
        await self.send(f"Jets/Tanks: {country.jets}/{country.tanks}")
        await self.send(f"Turrets/Spies: {country.turrets}/{country.spies}")
        await self.send(f"Readiness: {country.military_readiness}%")
        await self.send(f"Networth: {country.networth}")

    async def do_explore(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        turns = int(args[0]) if args else 1
        result = explore(
            country,
            turns=turns,
            now=db.now_ts(),
            rules=self.rules,
            rng=self.rng,
        )
        self.country = result.country
        db.save_country(self.conn, result.country)
        if result.news:
            db.add_news(self.conn, round_id=result.country.round_id, text=result.news)
        await self.send(result.message)
        await self.send_economy(result.economy)

    async def do_build(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if len(args) != 2:
            raise ValueError("Usage: BUILD FARMS amount")
        result = build(
            country,
            building=args[0],
            amount=int(args[1]),
            now=db.now_ts(),
            rules=self.rules,
        )
        self.country = result.country
        db.save_country(self.conn, result.country)
        if result.news:
            db.add_news(self.conn, round_id=result.country.round_id, text=result.news)
        await self.send(result.message)
        await self.send_economy(result.economy)

    async def do_cash(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        turns = int(args[0]) if args else 1
        result = cash_action(country, turns=turns, now=db.now_ts())
        self.country = result.country
        db.save_country(self.conn, result.country)
        await self.send(result.message)
        await self.send_economy(result.economy)

    async def send_economy(self, economy) -> None:
        if economy is None:
            return
        await self.send(f"Food {economy.food_delta:+d}")
        await self.send(f"Oil {economy.oil_delta:+d}")
        await self.send(f"Cash {economy.cash_delta:+d}")
        await self.send(f"Pop {economy.population_growth:+d}")
        produced = (
            economy.troops_produced
            + economy.jets_produced
            + economy.tanks_produced
            + economy.turrets_produced
        )
        if produced:
            await self.send(
                "Made "
                f"T{economy.troops_produced} "
                f"J{economy.jets_produced} "
                f"K{economy.tanks_produced} "
                f"U{economy.turrets_produced}"
            )

    async def do_research(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if len(args) != 2:
            raise ValueError("Usage: RESEARCH tech turns")
        result = research(
            country,
            tech=args[0],
            turns=int(args[1]),
            now=db.now_ts(),
            rules=self.rules,
        )
        self.country = result.country
        db.save_country(self.conn, result.country)
        await self.send(result.message)
        await self.send_economy(result.economy)

    async def do_produce(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        turns = int(args[0]) if args else 1
        result = produce_action(country, turns=turns, now=db.now_ts(), rules=self.rules)
        self.country = result.country
        db.save_country(self.conn, result.country)
        await self.send(result.message)
        await self.send_economy(result.economy)

    async def do_alloc(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if len(args) != 4:
            raise ValueError("Usage: ALLOC troops jets tanks turrets")
        result = set_industrial_allocation(
            country,
            troops=int(args[0]),
            jets=int(args[1]),
            tanks=int(args[2]),
            turrets=int(args[3]),
            now=db.now_ts(),
        )
        self.country = result.country
        db.save_country(self.conn, result.country)
        await self.send(result.message)

    async def show_market(self) -> None:
        await self.section("MARKET")
        await self.send("GOOD BUY SELL")
        for good, (buy, sell) in MARKET_PRICES.items():
            await self.send(f"{good[:7]:<7} {buy:<4} {sell:<4}")
        await self.send("BUY good amount")
        await self.send("SELL good amount")

    async def do_buy(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if len(args) != 2:
            raise ValueError("Usage: BUY good amount")
        result = buy_market(country, good=args[0], amount=int(args[1]), now=db.now_ts())
        self.country = result.country
        db.save_country(self.conn, result.country)
        await self.send(result.message)

    async def do_sell(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if len(args) != 2:
            raise ValueError("Usage: SELL good amount")
        result = sell_market(country, good=args[0], amount=int(args[1]), now=db.now_ts())
        self.country = result.country
        db.save_country(self.conn, result.country)
        await self.send(result.message)

    async def do_attack(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if not args:
            raise ValueError("Usage: ATTACK id STANDARD")
        target_id = int(args[0])
        if country.id == target_id:
            raise ValueError("Cannot attack yourself.")
        target = db.get_country_by_id(self.conn, country_id=target_id)
        if target is None:
            raise ValueError("No such country.")
        mode = args[1].upper() if len(args) > 1 else "STANDARD"
        if mode != "STANDARD":
            raise ValueError("Only STANDARD is implemented.")
        result = standard_strike(
            country,
            target,
            now=db.now_ts(),
            rules=self.rules,
            rng=self.rng,
        )
        self.country = result.attacker
        db.save_country(self.conn, result.attacker)
        db.save_country(self.conn, result.defender)
        if result.news:
            db.add_news(self.conn, round_id=result.attacker.round_id, text=result.news)
        await self.send(result.message)

    async def do_spy(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if not args:
            raise ValueError("Usage: SPY id INTEL")
        target = db.get_country_by_id(self.conn, country_id=int(args[0]))
        if target is None:
            raise ValueError("No such country.")
        op = args[1].upper() if len(args) > 1 else "INTEL"
        if op != "INTEL":
            raise ValueError("Only INTEL is implemented.")
        result = spy_intel(country, target, now=db.now_ts(), rng=self.rng)
        self.country = result.country
        db.save_country(self.conn, result.country)
        await self.send(result.message)

    async def do_missile(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if len(args) != 2:
            raise ValueError("Usage: MISSILE id type")
        target = db.get_country_by_id(self.conn, country_id=int(args[0]))
        if target is None:
            raise ValueError("No such country.")
        result = launch_missile(
            country,
            target,
            missile=args[1],
            now=db.now_ts(),
            rng=self.rng,
        )
        self.country = result.attacker
        db.save_country(self.conn, result.attacker)
        db.save_country(self.conn, result.defender)
        if result.news:
            db.add_news(self.conn, round_id=result.attacker.round_id, text=result.news)
        await self.send(result.message)

    async def do_ally(self, args: list[str]) -> None:
        await self.refresh_country()
        country = self.require_country()
        if len(args) != 1:
            raise ValueError("Usage: ALLY id")
        if country.id is None:
            raise ValueError("Save country first.")
        target_id = int(args[0])
        target = db.get_country_by_id(self.conn, country_id=target_id)
        if target is None:
            raise ValueError("No such country.")
        db.add_alliance(self.conn, country_a=country.id, country_b=target_id)
        db.add_news(
            self.conn,
            round_id=country.round_id,
            text=f"{country.name} proposed alliance with {target.name}.",
        )
        await self.send("Alliance proposed.")

    async def show_scores(self) -> None:
        await self.section("TOP COUNTRIES")
        countries = score_rows(db.list_countries(self.conn))[:10]
        if not countries:
            await self.send("No countries yet.")
            return
        for idx, country in enumerate(countries, 1):
            line = f"{idx:>2} {country.name[:16]:<16} {country.networth}"
            await self.send(line)

    async def show_news(self) -> None:
        await self.section("NEWS")
        rows = db.list_news(self.conn, limit=8)
        if not rows:
            await self.send("No news yet.")
            return
        for row in rows:
            await self.send(f"* {row['text']}")


async def serve(config: ServerConfig) -> None:
    conn = db.connect(config.db_path)
    try:
        db.initialize(conn)
    finally:
        conn.close()

    http_server = None
    if config.http_port is not None:
        http_server = start_http_server(
            config.db_path,
            config.http_host,
            config.http_port,
        )

    async def client_connected(reader, writer) -> None:
        session = TerminalSession(reader, writer, config)
        await session.run()

    server = await asyncio.start_server(client_connected, config.host, config.port)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signame in {"SIGINT", "SIGTERM"}:
        if hasattr(signal, signame):
            try:
                loop.add_signal_handler(getattr(signal, signame), stop_event.set)
            except NotImplementedError:
                pass

    sockets = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Earth 2064 TCP listening on {sockets}")
    if http_server:
        host, port = http_server.server_address
        print(f"Earth 2064 web status on http://{host}:{port}")
    try:
        async with server:
            await stop_event.wait()
    finally:
        server.close()
        await server.wait_closed()
        if http_server:
            http_server.shutdown()
            http_server.server_close()


def parse_args(argv: list[str] | None = None) -> ServerConfig:
    parser = argparse.ArgumentParser(description="Run the Earth 2064 server.")
    parser.add_argument("--db", default="var/earth2064.sqlite")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2064)
    parser.add_argument("--http-host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--no-http", action="store_true")
    parser.add_argument("--turn-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    return ServerConfig(
        db_path=str(Path(args.db)),
        host=args.host,
        port=args.port,
        http_host=args.http_host,
        http_port=None if args.no_http else args.http_port,
        turn_seconds=max(1, args.turn_seconds),
    )


def main(argv: list[str] | None = None) -> None:
    config = parse_args(argv)
    try:
        asyncio.run(serve(config))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
