from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlparse

from . import db
from .core import score_rows


def country_payload(country) -> dict[str, object]:
    return {
        "id": country.id,
        "name": country.name,
        "ruler": country.ruler,
        "land": country.land,
        "turns": country.turns,
        "networth": country.networth,
    }


def make_handler(db_path: str):
    class StatusHandler(BaseHTTPRequestHandler):
        server_version = "Earth2064HTTP/0.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/scores":
                self.send_scores_json()
                return
            if parsed.path == "/":
                self.send_index()
                return
            self.send_error(404, "Not found")

        def send_scores_json(self) -> None:
            conn = db.connect(db_path)
            try:
                db.initialize(conn)
                scores = [country_payload(c) for c in score_rows(db.list_countries(conn))]
            finally:
                conn.close()
            body = json.dumps({"scores": scores}, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_index(self) -> None:
            conn = db.connect(db_path)
            try:
                db.initialize(conn)
                scores = score_rows(db.list_countries(conn))[:10]
                news = db.list_news(conn, limit=8)
            finally:
                conn.close()

            score_items = "\n".join(
                "<tr>"
                f"<td>{idx}</td>"
                f"<td>{html.escape(country.name)}</td>"
                f"<td>{html.escape(country.ruler)}</td>"
                f"<td>{country.land}</td>"
                f"<td>{country.networth}</td>"
                "</tr>"
                for idx, country in enumerate(scores, 1)
            )
            news_items = "\n".join(
                f"<li>{html.escape(row['text'])}</li>"
                for row in news
            )
            body = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Earth 2064</title>
<style>
body {{
  margin: 2rem;
  font: 16px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #10140f;
  color: #edf5df;
}}
a {{ color: #9bd67b; }}
table {{ border-collapse: collapse; min-width: 34rem; max-width: 100%; }}
th, td {{ border-bottom: 1px solid #34412d; padding: .35rem .6rem; text-align: left; }}
.shell {{ color: #9bd67b; }}
</style>
<h1>EARTH 2064</h1>
<p>Local prototype. Terminal: <span class="shell">nc 127.0.0.1 2064</span></p>
<h2>Top Countries</h2>
<table>
<thead><tr><th>#</th><th>Country</th><th>Ruler</th><th>Land</th><th>Net</th></tr></thead>
<tbody>{score_items or '<tr><td colspan="5">No countries yet.</td></tr>'}</tbody>
</table>
<h2>News</h2>
<ul>{news_items or '<li>No news yet.</li>'}</ul>
</html>
"""
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return StatusHandler


def start_http_server(db_path: str, host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(db_path))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
