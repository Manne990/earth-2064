import asyncio
from unittest import TestCase

from earth2064.server import BUILD_MENU, MAIN_MENU, TerminalSession, menu_choice


class FakeWriter:
    def get_extra_info(self, name):
        return None


class TerminalInputTests(TestCase):
    def read_line(self, payload: bytes) -> str | None:
        async def run():
            reader = asyncio.StreamReader()
            reader.feed_data(payload)
            reader.feed_eof()
            session = TerminalSession.__new__(TerminalSession)
            session.reader = reader
            session.pending_input = bytearray()
            return await TerminalSession.read_command(session)

        return asyncio.run(run())

    def test_reads_lf_terminated_commands(self) -> None:
        self.assertEqual(self.read_line(b"HELP\n"), "HELP")

    def test_reads_cr_terminated_commands(self) -> None:
        self.assertEqual(self.read_line(b"HELP\r"), "HELP")

    def test_reads_crlf_terminated_commands(self) -> None:
        self.assertEqual(self.read_line(b"HELP\r\n"), "HELP")

    def test_main_menu_has_earthlike_browser_shape(self) -> None:
        labels = [item[1] for item in MAIN_MENU]

        self.assertEqual(labels[:4], ["ADVISOR", "BUILD", "CASH", "EXPLORE"])
        self.assertIn("WAR ROOM", labels)
        self.assertIn("SCORES", labels)

    def test_build_menu_numeric_choices_map_to_buildings(self) -> None:
        self.assertEqual(menu_choice(BUILD_MENU, "1")[1], "farms")
        self.assertEqual(menu_choice(BUILD_MENU, "5")[1], "labs")
        self.assertIsNone(menu_choice(BUILD_MENU, "9"))
