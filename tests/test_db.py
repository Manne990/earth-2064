import sqlite3
from unittest import TestCase

from earth2064 import db
from earth2064.core import GameRules


class DatabaseTests(TestCase):
    def test_create_country_persists_earthlike_fields(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        db.initialize(conn)
        user_id = db.create_user(conn, "tester", "swordfish")

        country = db.create_country(
            conn,
            user_id=user_id,
            ruler="tester",
            name="Persistia",
            rules=GameRules(),
        )

        self.assertEqual(country.government, "monarchy")
        self.assertGreater(country.oil, 0)
        self.assertGreater(country.troops, 0)

    def test_add_alliance_records_pair_once(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        db.initialize(conn)
        a_user = db.create_user(conn, "alpha", "swordfish")
        b_user = db.create_user(conn, "bravo", "swordfish")
        a = db.create_country(
            conn,
            user_id=a_user,
            ruler="alpha",
            name="Alpha Land",
            rules=GameRules(),
        )
        b = db.create_country(
            conn,
            user_id=b_user,
            ruler="bravo",
            name="Bravo Land",
            rules=GameRules(),
        )

        db.add_alliance(conn, country_a=a.id, country_b=b.id)
        db.add_alliance(conn, country_a=b.id, country_b=a.id)

        count = conn.execute("SELECT COUNT(*) AS count FROM alliances").fetchone()["count"]
        self.assertEqual(count, 1)
