"""Disposable HTTP target with a separate SQLite audit evidence path.

Run on the isolated lab host only. No model or engine imports belong here.
The HTTP handler cannot reset or patch itself; those are controller operations.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class LiveLab:
    def __init__(self, database: Path, case: str):
        self.database = database
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS state (patched INTEGER);"
                "CREATE TABLE IF NOT EXISTS audit (subject TEXT, status INTEGER);"
            )
        self.reset(case)
        lab = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path == "/health":
                    status, payload = 200, {"healthy": True}
                elif self.path == "/activity":
                    with lab.connect() as db:
                        rows = db.execute(
                            "SELECT rowid, subject, status FROM audit WHERE subject='owner'"
                        ).fetchall()
                    status, payload = (
                        200,
                        {
                            "owner_activity": [
                                {
                                    "request_id": row[0],
                                    "account": row[1],
                                    "status": row[2],
                                    "route": "/profile/owner",
                                    "classification": "legitimate_background",
                                }
                                for row in rows
                            ]
                        },
                    )
                elif self.path in ("/profile/owner", "/profile/other"):
                    subject = self.path.rsplit("/", 1)[-1]
                    with lab.connect() as db:
                        patched = db.execute("SELECT patched FROM state").fetchone()[0]
                        status = 403 if patched and subject == "other" else 200
                        db.execute("INSERT INTO audit VALUES (?, ?)", (subject, status))
                    payload = {"account": subject} if status == 200 else {"error": "forbidden"}
                else:
                    status, payload = 404, {"error": "not found"}
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reset(self, case: str):
        if case not in {"success", "failed", "pre_satisfied", "patched_control"}:
            raise ValueError("unknown lab case")
        with self.connect() as db:
            db.execute("DELETE FROM state")
            db.execute("DELETE FROM audit")
            db.execute("INSERT INTO state VALUES (?)", (int(case == "patched_control"),))
            if case == "pre_satisfied":
                db.execute("INSERT INTO audit VALUES ('other', 200)")

    def snapshot(self):
        with self.connect() as db:
            return {
                "breaches": db.execute(
                    "SELECT COUNT(*) FROM audit WHERE subject='other' AND status=200"
                ).fetchone()[0],
                "events": db.execute("SELECT COUNT(*) FROM audit").fetchone()[0],
                "blocked": db.execute(
                    "SELECT COUNT(*) FROM audit WHERE subject='other' AND status=403"
                ).fetchone()[0],
                "owner_ok": db.execute(
                    "SELECT COUNT(*) FROM audit WHERE subject='owner' AND status=200"
                ).fetchone()[0],
            }

    def request(self, subject: str):
        if subject not in {"owner", "other", "activity"}:
            raise ValueError("subject outside owned lab")
        path = "/activity" if subject == "activity" else f"/profile/{subject}"
        url = f"http://127.0.0.1:{self.server.server_port}{path}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(url, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return {"status": response.code, "body": json.load(response), "subject": subject}

    def verify(self, before: dict, result: dict):
        if before["breaches"]:
            return "UNVERIFIABLE_PRE_SATISFIED"
        primary = result["status"] == 200 and result["body"].get("account") == "other"
        shadow = self.snapshot()["breaches"] > before["breaches"]
        if primary != shadow:
            return "QUARANTINED_VERIFIER_DISAGREEMENT"
        return "VERIFIED" if primary else "NOT_VERIFIED"

    def patch(self):
        with self.connect() as db:
            db.execute("UPDATE state SET patched=1")

    def health(self):
        url = f"http://127.0.0.1:{self.server.server_port}/health"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=5) as response:
            return response.status == 200 and json.load(response) == {"healthy": True}

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
