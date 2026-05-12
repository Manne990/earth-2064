from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
import time
from pathlib import Path

from .core import Country, GameRules, new_country


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
COUNTRY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _'-]{2,23}$")


def now_ts() -> int:
    return int(time.time())


def connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            starts_at INTEGER NOT NULL,
            ends_at INTEGER,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            round_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            ruler TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            last_turn_at INTEGER NOT NULL,
            turns INTEGER NOT NULL,
            land INTEGER NOT NULL,
            population INTEGER NOT NULL,
            food INTEGER NOT NULL,
            cash INTEGER NOT NULL,
            technology INTEGER NOT NULL,
            farms INTEGER NOT NULL,
            industry INTEGER NOT NULL,
            labs INTEGER NOT NULL,
            residences INTEGER NOT NULL,
            bases INTEGER NOT NULL,
            defense INTEGER NOT NULL,
            construction INTEGER NOT NULL DEFAULT 0,
            UNIQUE(round_id, user_id),
            UNIQUE(round_id, name COLLATE NOCASE),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(round_id) REFERENCES rounds(id)
        );

        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY(round_id) REFERENCES rounds(id)
        );
        """
    )
    conn.commit()
    ensure_active_round(conn)


def ensure_active_round(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM rounds WHERE status = 'active' ORDER BY id LIMIT 1"
    ).fetchone()
    if row:
        return row

    created = now_ts()
    cur = conn.execute(
        "INSERT INTO rounds (name, starts_at, ends_at, status) VALUES (?, ?, NULL, ?)",
        ("Alpha Test", created, "active"),
    )
    conn.execute(
        "INSERT INTO news (round_id, created_at, text) VALUES (?, ?, ?)",
        (cur.lastrowid, created, "Alpha Test round has opened."),
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM rounds WHERE status = 'active' ORDER BY id LIMIT 1"
    ).fetchone()


def active_round_id(conn: sqlite3.Connection) -> int:
    return int(ensure_active_round(conn)["id"])


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if len(password) < 4:
        raise ValueError("Password must be at least 4 chars.")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000,
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    if len(password) < 4:
        return False
    salt = bytes.fromhex(salt_hex)
    _, check = hash_password(password, salt)
    return hmac.compare_digest(check, digest_hex)


def validate_username(username: str) -> str:
    username = username.strip()
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Username: 3-20 letters/numbers/_.")
    return username


def validate_country_name(name: str) -> str:
    name = " ".join(name.strip().split())
    if not COUNTRY_RE.fullmatch(name):
        raise ValueError("Country name: 3-24 ASCII chars.")
    return name


def create_user(conn: sqlite3.Connection, username: str, password: str) -> int:
    username = validate_username(username)
    salt, digest = hash_password(password)
    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, salt, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, salt, digest, now_ts()),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("Username already exists.") from exc
    return int(cur.lastrowid)


def authenticate(conn: sqlite3.Connection, username: str, password: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
        (username.strip(),),
    ).fetchone()
    if not row or not verify_password(password, row["salt"], row["password_hash"]):
        raise ValueError("Bad username or password.")
    return row


def row_to_country(row: sqlite3.Row) -> Country:
    return Country(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        round_id=int(row["round_id"]),
        name=str(row["name"]),
        ruler=str(row["ruler"]),
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
        last_turn_at=int(row["last_turn_at"]),
        turns=int(row["turns"]),
        land=int(row["land"]),
        population=int(row["population"]),
        food=int(row["food"]),
        cash=int(row["cash"]),
        technology=int(row["technology"]),
        farms=int(row["farms"]),
        industry=int(row["industry"]),
        labs=int(row["labs"]),
        residences=int(row["residences"]),
        bases=int(row["bases"]),
        defense=int(row["defense"]),
        construction=int(row["construction"]),
    )


def country_to_values(country: Country) -> tuple[object, ...]:
    return (
        country.user_id,
        country.round_id,
        country.name,
        country.ruler,
        country.created_at,
        country.updated_at,
        country.last_turn_at,
        country.turns,
        country.land,
        country.population,
        country.food,
        country.cash,
        country.technology,
        country.farms,
        country.industry,
        country.labs,
        country.residences,
        country.bases,
        country.defense,
        country.construction,
    )


def create_country(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    ruler: str,
    name: str,
    rules: GameRules,
) -> Country:
    now = now_ts()
    country = new_country(
        user_id=user_id,
        round_id=active_round_id(conn),
        name=validate_country_name(name),
        ruler=ruler,
        now=now,
        rules=rules,
    )
    try:
        cur = conn.execute(
            """
            INSERT INTO countries (
                user_id, round_id, name, ruler, created_at, updated_at,
                last_turn_at, turns, land, population, food, cash,
                technology, farms, industry, labs, residences, bases,
                defense, construction
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            country_to_values(country),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("User or country already exists this round.") from exc
    return row_to_country(
        conn.execute("SELECT * FROM countries WHERE id = ?", (cur.lastrowid,)).fetchone()
    )


def get_country_for_user(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    round_id: int | None = None,
) -> Country | None:
    round_id = round_id or active_round_id(conn)
    row = conn.execute(
        "SELECT * FROM countries WHERE user_id = ? AND round_id = ?",
        (user_id, round_id),
    ).fetchone()
    return row_to_country(row) if row else None


def save_country(conn: sqlite3.Connection, country: Country) -> None:
    if country.id is None:
        raise ValueError("Country must have an id before save.")
    conn.execute(
        """
        UPDATE countries
        SET user_id = ?, round_id = ?, name = ?, ruler = ?,
            created_at = ?, updated_at = ?, last_turn_at = ?, turns = ?,
            land = ?, population = ?, food = ?, cash = ?, technology = ?,
            farms = ?, industry = ?, labs = ?, residences = ?, bases = ?,
            defense = ?, construction = ?
        WHERE id = ?
        """,
        (*country_to_values(country), country.id),
    )
    conn.commit()


def list_countries(conn: sqlite3.Connection, *, round_id: int | None = None) -> list[Country]:
    round_id = round_id or active_round_id(conn)
    rows = conn.execute(
        "SELECT * FROM countries WHERE round_id = ?",
        (round_id,),
    ).fetchall()
    return [row_to_country(row) for row in rows]


def add_news(conn: sqlite3.Connection, *, round_id: int, text: str) -> None:
    conn.execute(
        "INSERT INTO news (round_id, created_at, text) VALUES (?, ?, ?)",
        (round_id, now_ts(), text[:160]),
    )
    conn.commit()


def list_news(
    conn: sqlite3.Connection,
    *,
    round_id: int | None = None,
    limit: int = 8,
) -> list[sqlite3.Row]:
    round_id = round_id or active_round_id(conn)
    return conn.execute(
        """
        SELECT * FROM news
        WHERE round_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (round_id, limit),
    ).fetchall()
