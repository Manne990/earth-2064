import asyncio
from unittest import TestCase

from earth2064.server import TerminalSession


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
