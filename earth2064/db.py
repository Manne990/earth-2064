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

COUNTRY_COLUMNS: tuple[str, ...] = (
    "user_id",
    "round_id",
    "name",
    "ruler",
    "created_at",
    "updated_at",
    "last_turn_at",
    "turns",
    "land",
    "population",
    "food",
    "cash",
    "oil",
    "technology",
    "government",
    "tax_rate",
    "enterprise",
    "residences",
    "industry",
    "bases",
    "labs",
    "farms",
    "oil_rigs",
    "construction",
    "defense",
    "troops",
    "jets",
    "tanks",
    "turrets",
    "spies",
    "missiles_nuclear",
    "missiles_chemical",
    "missiles_cruise",
    "tech_military",
    "tech_medical",
    "tech_business",
    "tech_residential",
    "tech_agricultural",
    "tech_warfare",
    "tech_weapons",
    "tech_industrial",
    "tech_spy",
    "tech_sdi",
    "military_readiness",
    "spy_readiness",
    "industrial_troops",
    "industrial_jets",
    "industrial_tanks",
    "industrial_turrets",
)

COUNTRY_MIGRATIONS: dict[str, str] = {
    "oil": "INTEGER NOT NULL DEFAULT 1000",
    "government": "TEXT NOT NULL DEFAULT 'monarchy'",
    "tax_rate": "INTEGER NOT NULL DEFAULT 35",
    "enterprise": "INTEGER NOT NULL DEFAULT 10",
    "oil_rigs": "INTEGER NOT NULL DEFAULT 5",
    "troops": "INTEGER NOT NULL DEFAULT 120",
    "jets": "INTEGER NOT NULL DEFAULT 20",
    "tanks": "INTEGER NOT NULL DEFAULT 10",
    "turrets": "INTEGER NOT NULL DEFAULT 30",
    "spies": "INTEGER NOT NULL DEFAULT 25",
    "missiles_nuclear": "INTEGER NOT NULL DEFAULT 0",
    "missiles_chemical": "INTEGER NOT NULL DEFAULT 0",
    "missiles_cruise": "INTEGER NOT NULL DEFAULT 0",
    "tech_military": "INTEGER NOT NULL DEFAULT 0",
    "tech_medical": "INTEGER NOT NULL DEFAULT 0",
    "tech_business": "INTEGER NOT NULL DEFAULT 0",
    "tech_residential": "INTEGER NOT NULL DEFAULT 0",
    "tech_agricultural": "INTEGER NOT NULL DEFAULT 0",
    "tech_warfare": "INTEGER NOT NULL DEFAULT 0",
    "tech_weapons": "INTEGER NOT NULL DEFAULT 0",
    "tech_industrial": "INTEGER NOT NULL DEFAULT 0",
    "tech_spy": "INTEGER NOT NULL DEFAULT 0",
    "tech_sdi": "INTEGER NOT NULL DEFAULT 0",
    "military_readiness": "INTEGER NOT NULL DEFAULT 100",
    "spy_readiness": "INTEGER NOT NULL DEFAULT 100",
    "industrial_troops": "INTEGER NOT NULL DEFAULT 50",
    "industrial_jets": "INTEGER NOT NULL DEFAULT 20",
    "industrial_tanks": "INTEGER NOT NULL DEFAULT 20",
    "industrial_turrets": "INTEGER NOT NULL DEFAULT 10",
}


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
            oil INTEGER NOT NULL DEFAULT 1000,
            technology INTEGER NOT NULL DEFAULT 0,
            government TEXT NOT NULL DEFAULT 'monarchy',
            tax_rate INTEGER NOT NULL DEFAULT 35,
            enterprise INTEGER NOT NULL DEFAULT 10,
            residences INTEGER NOT NULL,
            industry INTEGER NOT NULL,
            bases INTEGER NOT NULL,
            labs INTEGER NOT NULL,
            farms INTEGER NOT NULL,
            oil_rigs INTEGER NOT NULL DEFAULT 5,
            construction INTEGER NOT NULL DEFAULT 0,
            defense INTEGER NOT NULL DEFAULT 0,
            troops INTEGER NOT NULL DEFAULT 120,
            jets INTEGER NOT NULL DEFAULT 20,
            tanks INTEGER NOT NULL DEFAULT 10,
            turrets INTEGER NOT NULL DEFAULT 30,
            spies INTEGER NOT NULL DEFAULT 25,
            missiles_nuclear INTEGER NOT NULL DEFAULT 0,
            missiles_chemical INTEGER NOT NULL DEFAULT 0,
            missiles_cruise INTEGER NOT NULL DEFAULT 0,
            tech_military INTEGER NOT NULL DEFAULT 0,
            tech_medical INTEGER NOT NULL DEFAULT 0,
            tech_business INTEGER NOT NULL DEFAULT 0,
            tech_residential INTEGER NOT NULL DEFAULT 0,
            tech_agricultural INTEGER NOT NULL DEFAULT 0,
            tech_warfare INTEGER NOT NULL DEFAULT 0,
            tech_weapons INTEGER NOT NULL DEFAULT 0,
            tech_industrial INTEGER NOT NULL DEFAULT 0,
            tech_spy INTEGER NOT NULL DEFAULT 0,
            tech_sdi INTEGER NOT NULL DEFAULT 0,
            military_readiness INTEGER NOT NULL DEFAULT 100,
            spy_readiness INTEGER NOT NULL DEFAULT 100,
            industrial_troops INTEGER NOT NULL DEFAULT 50,
            industrial_jets INTEGER NOT NULL DEFAULT 20,
            industrial_tanks INTEGER NOT NULL DEFAULT 20,
            industrial_turrets INTEGER NOT NULL DEFAULT 10,
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

        CREATE TABLE IF NOT EXISTS alliances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER NOT NULL,
            country_a INTEGER NOT NULL,
            country_b INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            UNIQUE(round_id, country_a, country_b),
            FOREIGN KEY(round_id) REFERENCES rounds(id),
            FOREIGN KEY(country_a) REFERENCES countries(id),
            FOREIGN KEY(country_b) REFERENCES countries(id)
        );
        """
    )
    migrate_countries(conn)
    conn.commit()
    ensure_active_round(conn)


def migrate_countries(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(countries)").fetchall()
    }
    for column, definition in COUNTRY_MIGRATIONS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE countries ADD COLUMN {column} {definition}")


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
        oil=int(row["oil"]),
        technology=int(row["technology"]),
        government=str(row["government"]),
        tax_rate=int(row["tax_rate"]),
        enterprise=int(row["enterprise"]),
        residences=int(row["residences"]),
        industry=int(row["industry"]),
        bases=int(row["bases"]),
        labs=int(row["labs"]),
        farms=int(row["farms"]),
        oil_rigs=int(row["oil_rigs"]),
        construction=int(row["construction"]),
        defense=int(row["defense"]),
        troops=int(row["troops"]),
        jets=int(row["jets"]),
        tanks=int(row["tanks"]),
        turrets=int(row["turrets"]),
        spies=int(row["spies"]),
        missiles_nuclear=int(row["missiles_nuclear"]),
        missiles_chemical=int(row["missiles_chemical"]),
        missiles_cruise=int(row["missiles_cruise"]),
        tech_military=int(row["tech_military"]),
        tech_medical=int(row["tech_medical"]),
        tech_business=int(row["tech_business"]),
        tech_residential=int(row["tech_residential"]),
        tech_agricultural=int(row["tech_agricultural"]),
        tech_warfare=int(row["tech_warfare"]),
        tech_weapons=int(row["tech_weapons"]),
        tech_industrial=int(row["tech_industrial"]),
        tech_spy=int(row["tech_spy"]),
        tech_sdi=int(row["tech_sdi"]),
        military_readiness=int(row["military_readiness"]),
        spy_readiness=int(row["spy_readiness"]),
        industrial_troops=int(row["industrial_troops"]),
        industrial_jets=int(row["industrial_jets"]),
        industrial_tanks=int(row["industrial_tanks"]),
        industrial_turrets=int(row["industrial_turrets"]),
    )


def country_to_values(country: Country) -> tuple[object, ...]:
    return tuple(getattr(country, column) for column in COUNTRY_COLUMNS)


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
    columns = ", ".join(COUNTRY_COLUMNS)
    placeholders = ", ".join("?" for _ in COUNTRY_COLUMNS)
    try:
        cur = conn.execute(
            f"INSERT INTO countries ({columns}) VALUES ({placeholders})",
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


def get_country_by_id(
    conn: sqlite3.Connection,
    *,
    country_id: int,
    round_id: int | None = None,
) -> Country | None:
    round_id = round_id or active_round_id(conn)
    row = conn.execute(
        "SELECT * FROM countries WHERE id = ? AND round_id = ?",
        (country_id, round_id),
    ).fetchone()
    return row_to_country(row) if row else None


def save_country(conn: sqlite3.Connection, country: Country) -> None:
    if country.id is None:
        raise ValueError("Country must have an id before save.")
    assignments = ", ".join(f"{column} = ?" for column in COUNTRY_COLUMNS)
    conn.execute(
        f"UPDATE countries SET {assignments} WHERE id = ?",
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


def add_alliance(conn: sqlite3.Connection, *, country_a: int, country_b: int) -> None:
    if country_a == country_b:
        raise ValueError("Cannot ally with yourself.")
    a, b = sorted((country_a, country_b))
    conn.execute(
        """
        INSERT OR IGNORE INTO alliances
            (round_id, country_a, country_b, status, created_at)
        VALUES (?, ?, ?, 'proposed', ?)
        """,
        (active_round_id(conn), a, b, now_ts()),
    )
    conn.commit()
