from __future__ import annotations

import argparse
import asyncio
import signal
from dataclasses import dataclass
from pathlib import Path
from random import Random

from . import db
from .core import GameRules, accrue_turns, build, cash_action, explore, score_rows
from .web import start_http_server


WIDTH = 40


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
            if command in {"QUIT", "EXIT"}:
                await self.send("Goodbye.")
                return False
            if command == "HELP":
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
                await self.do_build(args)
            elif command == "CASH" or command == "4":
                await self.do_cash(args)
            elif command == "SCORES" or command == "5":
                await self.show_scores()
            elif command == "NEWS" or command == "6":
                await self.show_news()
            else:
                await self.send("Unknown command. Type HELP.")
        except ValueError as exc:
            await self.send(f"ERR {exc}")
        return True

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
        await self.send("1 STATUS")
        await self.send("2 EXPLORE turns")
        await self.send("3 BUILD FARMS amount")
        await self.send("4 CASH turns")
        await self.send("5 SCORES")
        await self.send("6 NEWS")
        await self.send("QUIT")

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
        await self.send(f"Turns: {country.turns}/{self.rules.max_turns}")
        await self.send(f"Land: {country.land} acres")
        await self.send(f"Free land: {country.free_land}")
        await self.send(f"Population: {country.population}")
        await self.send(f"Food: {country.food}")
        await self.send(f"Cash: ${country.cash}")
        await self.send(f"Farms: {country.farms}")
        await self.send(f"Industry: {country.industry}")
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
        await self.send(f"Cash {economy.cash_delta:+d}")
        await self.send(f"Pop {economy.population_growth:+d}")

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
