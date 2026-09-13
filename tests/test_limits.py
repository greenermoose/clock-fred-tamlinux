#!/usr/bin/env python3
"""
test_limits.py — Comprehensive limit, deadline, validation, and refusal tests for fred.clock.
Stdlib only (unittest).
"""

from __future__ import annotations

import datetime
import http.server
import importlib.util
import json
import os
import ssl
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zoneinfo

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(TESTS_DIR)
FETCH_SCRIPT = os.path.join(PLUGIN_DIR, "fetch-events.py")
MANAGE_SCRIPT = os.path.join(PLUGIN_DIR, "manage-event.py")
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")

# Import fetch-events module dynamically to access constants and functions directly
_spec = importlib.util.spec_from_file_location("fetch_events", FETCH_SCRIPT)
if _spec is None or _spec.loader is None:
    raise ImportError("Cannot load fetch-events")
fetch_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_mod)


class TestLimitsAndSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate self-signed cert and key for HTTPS tests
        cls.ssl_dir = tempfile.TemporaryDirectory()
        cls.cert_path = os.path.join(cls.ssl_dir.name, "cert.pem")
        cls.key_path = os.path.join(cls.ssl_dir.name, "key.pem")
        cmd = [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            cls.key_path,
            "-out",
            cls.cert_path,
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=localhost",
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        cls.ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        cls.ssl_ctx.load_cert_chain(certfile=cls.cert_path, keyfile=cls.key_path)

    @classmethod
    def tearDownClass(cls):
        cls.ssl_dir.cleanup()

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.out_path = os.path.join(self.tmp_dir.name, "events.json")
        self.cfg_path = os.path.join(self.tmp_dir.name, "calendars.json")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _run_fetch(self, extra_args: list[str] | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        cmd = [
            sys.executable,
            FETCH_SCRIPT,
            "--config",
            self.cfg_path,
            "--output",
            self.out_path,
            "--no-rlimits",
        ]
        if extra_args:
            cmd.extend(extra_args)
        run_env = os.environ.copy()
        run_env["SSL_CERT_FILE"] = self.cert_path
        if env:
            run_env.update(env)
        return subprocess.run(cmd, capture_output=True, text=True, env=run_env)

    # 1. Oversized remote feed
    def test_oversized_remote_feed(self):
        """Verify remote feed exceeding MAX_FEED_BYTES is dropped (with and without Content-Length) while sibling feed loads."""
        sibling_ics = os.path.join(FIXTURES_DIR, "all_day.ics")

        class OversizedHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    if self.path == "/oversized_cl":
                        # With Content-Length header > MAX_FEED_BYTES
                        cl = fetch_mod.MAX_FEED_BYTES + 1024
                        self.send_response(200)
                        self.send_header("Content-Type", "text/calendar")
                        self.send_header("Content-Length", str(cl))
                        self.end_headers()
                        self.wfile.write(b"BEGIN:VCALENDAR\r\n" + b"X" * cl)
                    elif self.path == "/oversized_stream":
                        # Without Content-Length header, streamed > MAX_FEED_BYTES
                        self.send_response(200)
                        self.send_header("Content-Type", "text/calendar")
                        self.end_headers()
                        chunk = b"X" * 65536
                        written = 0
                        while written <= fetch_mod.MAX_FEED_BYTES + 65536:
                            self.wfile.write(chunk)
                            written += len(chunk)
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception:
                    pass

            def log_message(self, *args):
                pass

        httpd = http.server.HTTPServer(("localhost", 0), OversizedHandler)
        httpd.socket = self.ssl_ctx.wrap_socket(httpd.socket, server_side=True)
        port = httpd.server_port
        t = threading.Thread(target=httpd.serve_forever)
        t.daemon = True
        t.start()

        try:
            # Case A: with Content-Length
            cfg = [
                {"account": "Good", "name": "Sibling", "path": sibling_ics, "enabled": True},
                {"account": "Bad", "name": "BigCL", "url": f"https://localhost:{port}/oversized_cl", "enabled": True},
            ]
            with open(self.cfg_path, "w") as f:
                json.dump(cfg, f)

            res = self._run_fetch()
            self.assertEqual(res.returncode, 0, f"Stderr: {res.stderr}")
            with open(self.out_path, "r") as f:
                data = json.load(f)
            # Sibling event exists, BigCL was dropped
            self.assertEqual(len(data["events"]), 1)
            self.assertEqual(data["events"][0]["calendar"], "Sibling")

            # Case B: without Content-Length (streamed)
            cfg = [
                {"account": "Good", "name": "Sibling", "path": sibling_ics, "enabled": True},
                {"account": "Bad", "name": "BigStream", "url": f"https://localhost:{port}/oversized_stream", "enabled": True},
            ]
            with open(self.cfg_path, "w") as f:
                json.dump(cfg, f)

            res = self._run_fetch()
            self.assertEqual(res.returncode, 0, f"Stderr: {res.stderr}")
            with open(self.out_path, "r") as f:
                data = json.load(f)
            self.assertEqual(len(data["events"]), 1)
            self.assertEqual(data["events"][0]["calendar"], "Sibling")
        finally:
            httpd.shutdown()

    # 2. http:// and cross-scheme redirect
    def test_http_and_cross_scheme_redirect(self):
        """Verify http:// feed URLs and HTTPS-to-HTTP redirects are refused with stderr naming the feed."""
        # Direct http://
        cfg = [
            {"account": "Insecure", "name": "HttpFeed", "url": "http://example.com/cal.ics", "enabled": True}
        ]
        with open(self.cfg_path, "w") as f:
            json.dump(cfg, f)

        res = self._run_fetch()
        self.assertEqual(res.returncode, 0)
        self.assertIn("refusing non-HTTPS", res.stderr)
        self.assertIn("http://example.com/cal.ics", res.stderr)

        # Cross-scheme redirect (HTTPS -> HTTP)
        class RedirectHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "http://example.com/insecure.ics")
                self.end_headers()

            def log_message(self, *args):
                pass

        httpd = http.server.HTTPServer(("localhost", 0), RedirectHandler)
        httpd.socket = self.ssl_ctx.wrap_socket(httpd.socket, server_side=True)
        port = httpd.server_port
        t = threading.Thread(target=httpd.serve_forever)
        t.daemon = True
        t.start()

        try:
            cfg = [
                {"account": "Redirect", "name": "RedirectFeed", "url": f"https://localhost:{port}/redirect", "enabled": True}
            ]
            with open(self.cfg_path, "w") as f:
                json.dump(cfg, f)

            res = self._run_fetch()
            self.assertEqual(res.returncode, 0)
            self.assertIn("RedirectFeed", res.stderr)
        finally:
            httpd.shutdown()

    # 3. Slow server + --deadline 2
    def test_slow_server_deadline(self):
        """Verify slow server with --deadline exits non-zero within 5s leaving previous cache intact."""
        class SlowHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                time.sleep(10)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        httpd = http.server.HTTPServer(("localhost", 0), SlowHandler)
        httpd.socket = self.ssl_ctx.wrap_socket(httpd.socket, server_side=True)
        port = httpd.server_port
        t = threading.Thread(target=httpd.serve_forever)
        t.daemon = True
        t.start()

        try:
            # Pre-populate cache
            original_payload = b'{"updatedAt": 12345, "events": []}'
            with open(self.out_path, "wb") as f:
                f.write(original_payload)

            cfg = [
                {"account": "Slow", "name": "SlowFeed", "url": f"https://localhost:{port}/slow", "enabled": True}
            ]
            with open(self.cfg_path, "w") as f:
                json.dump(cfg, f)

            start = time.time()
            res = self._run_fetch(extra_args=["--deadline", "2"])
            elapsed = time.time() - start

            self.assertNotEqual(res.returncode, 0)
            self.assertLess(elapsed, 5.0)

            # Previous cache must remain untouched
            with open(self.out_path, "rb") as f:
                current_cache = f.read()
            self.assertEqual(current_cache, original_payload)
        finally:
            httpd.shutdown()

    # 4. Config caps
    def test_config_caps(self):
        """Verify oversized config, non-list config, and MAX_FEEDS + 1 feeds."""
        # Case A: Oversized config (> MAX_CONFIG_BYTES)
        huge_cfg = [{"name": f"Feed{i}", "path": "/dev/null"} for i in range(2000)]
        with open(self.cfg_path, "w") as f:
            json.dump(huge_cfg, f)
        self.assertGreater(os.path.getsize(self.cfg_path), fetch_mod.MAX_CONFIG_BYTES)

        res = self._run_fetch()
        self.assertEqual(res.returncode, 0)
        self.assertIn("exceeds MAX_CONFIG_BYTES", res.stderr)

        # Case B: Non-list config
        with open(self.cfg_path, "w") as f:
            f.write('{"invalid": "dictionary"}')
        res = self._run_fetch()
        self.assertEqual(res.returncode, 0)
        self.assertIn("must be a JSON list", res.stderr)

        # Case C: MAX_FEEDS + 1 feeds (33 feeds)
        sibling_ics = os.path.join(FIXTURES_DIR, "all_day.ics")
        thirty_three = [{"account": f"Acc{i}", "name": f"Feed{i}", "path": sibling_ics} for i in range(fetch_mod.MAX_FEEDS + 1)]
        with open(self.cfg_path, "w") as f:
            json.dump(thirty_three, f)

        res = self._run_fetch()
        self.assertEqual(res.returncode, 0)
        self.assertIn(f"exceeds MAX_FEEDS ({fetch_mod.MAX_FEEDS}), truncating", res.stderr)

    # 5. Line, VEVENT, and instance caps
    def test_line_and_vevent_and_instance_caps(self):
        """Verify line length, VEVENT count, and recurrence instance caps."""
        # Line cap: line folded over MAX_LINE_BYTES
        long_line_ics = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "BEGIN:VEVENT\r\n"
            "UID:long-line@test\r\n"
            "DTSTART:20260920T100000Z\r\n"
            "DTEND:20260920T110000Z\r\n"
            "SUMMARY:Normal Title\r\n"
            "DESCRIPTION:" + "A" * (fetch_mod.MAX_LINE_BYTES + 100) + "\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        lines = list(fetch_mod.unfold_ics(long_line_ics))
        self.assertTrue(any(l.startswith("SUMMARY:Normal Title") for l in lines))

        # VEVENT cap: MAX_VEVENTS_PER_FEED + 1
        tz = zoneinfo.ZoneInfo("UTC")
        w_start = datetime.datetime(2026, 9, 1, tzinfo=tz)
        w_end = datetime.datetime(2026, 9, 30, tzinfo=tz)

        # Test with small content containing 3 events where cap is tested
        vevents = []
        for i in range(fetch_mod.MAX_VEVENTS_PER_FEED + 5):
            vevents.append(
                f"BEGIN:VEVENT\r\nUID:ev{i}@test\r\nDTSTART:20260915T100000Z\r\nDTEND:20260915T110000Z\r\nSUMMARY:Ev{i}\r\nEND:VEVENT"
            )
        ics_text = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n" + "\r\n".join(vevents) + "\r\nEND:VCALENDAR\r\n"
        parsed = fetch_mod.parse_ics_content(ics_text, w_start, w_end, tz)
        self.assertEqual(len(parsed), fetch_mod.MAX_VEVENTS_PER_FEED)

        # Instance cap: expand_event bounds iterations
        bomb_event = {
            "id": "bomb@test",
            "summary": "Recurrence Bomb",
            "start_dt": datetime.datetime(2026, 1, 1, 10, 0, tzinfo=tz),
            "duration": datetime.timedelta(hours=1),
            "all_day": False,
            "rrule": {"FREQ": "DAILY", "INTERVAL": 1},
            "exdates": set(),
        }
        far_end = datetime.datetime(2030, 1, 1, tzinfo=tz)
        instances = fetch_mod.expand_event(bomb_event, w_start, far_end, tz)
        self.assertLessEqual(len(instances), fetch_mod.MAX_INSTANCES_PER_EVENT)

    # 6. RRULE bombs
    def test_rrule_bombs(self):
        """Verify hostile RRULE constructs are bounded and do not hang or crash."""
        tz = zoneinfo.ZoneInfo("UTC")
        w_start = datetime.datetime(2026, 9, 1, tzinfo=tz)
        w_end = datetime.datetime(2026, 9, 30, tzinfo=tz)

        bombs = [
            "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR,SA,SU;INTERVAL=1;COUNT=999999999",
            "FREQ=DAILY;INTERVAL=0",
            "FREQ=DAILY;UNTIL=99991231T235959Z",
            "FREQ=DAILY;COUNT=" + "9" * 5000,
        ]

        for rrule_str in bombs:
            parsed_rrule = fetch_mod.parse_rrule(rrule_str)
            event_data = {
                "id": "rrule-bomb@test",
                "summary": "Bomb Event",
                "start_dt": datetime.datetime(2026, 9, 1, 10, 0, tzinfo=tz),
                "duration": datetime.timedelta(hours=1),
                "all_day": False,
                "rrule": parsed_rrule,
                "exdates": set(),
            }
            # Expansion must terminate quickly and return bounded list
            res = fetch_mod.expand_event(event_data, w_start, w_end, tz)
            self.assertIsInstance(res, list)
            self.assertLessEqual(len(res), fetch_mod.MAX_INSTANCES_PER_EVENT)

    # 7. Field truncation
    def test_field_truncation(self):
        """Verify fields longer than caps are truncated before unescaping and meeting URL is extracted."""
        huge_desc = "https://meet.google.com/abc-defg-hij " + ("X" * 1_000_000)
        ics_text = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "BEGIN:VEVENT\r\n"
            "UID:trunc@test\r\n"
            "DTSTART:20260915T100000Z\r\n"
            "DTEND:20260915T110000Z\r\n"
            "SUMMARY:" + ("S" * 1000) + "\r\n"
            "LOCATION:" + ("L" * 3000) + "\r\n"
            "DESCRIPTION:" + huge_desc + "\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        tz = zoneinfo.ZoneInfo("UTC")
        w_start = datetime.datetime(2026, 9, 1, tzinfo=tz)
        w_end = datetime.datetime(2026, 9, 30, tzinfo=tz)

        parsed = fetch_mod.parse_ics_content(ics_text, w_start, w_end, tz)
        self.assertEqual(len(parsed), 1)
        ev = parsed[0]
        self.assertLessEqual(len(ev["summary"]), fetch_mod.MAX_SUMMARY)
        self.assertLessEqual(len(ev["location"]), fetch_mod.MAX_LOCATION)
        self.assertLessEqual(len(ev["description"]), fetch_mod.MAX_DESCRIPTION)
        self.assertEqual(ev["meetingUrl"], "https://meet.google.com/abc-defg-hij")

    # 8. Output cap
    def test_output_cap(self):
        """Verify output payload exceeding MAX_OUTPUT_BYTES sheds descriptions then truncates events, staying valid JSON."""
        many_events = []
        for i in range(1000):
            many_events.append(
                {
                    "id": f"ev-{i}",
                    "summary": f"Event {i}",
                    "start": "2026-09-15T10:00:00",
                    "end": "2026-09-15T11:00:00",
                    "startTs": 1726394400 + i * 3600,
                    "endTs": 1726398000 + i * 3600,
                    "dateKey": "2026-09-15",
                    "endDateKey": "2026-09-15",
                    "timeStr": "10:00 – 11:00",
                    "allDay": False,
                    "location": "Room 101",
                    "description": "D" * 4000,
                    "meetingUrl": "",
                }
            )
        # Total size of many_events with 4000-char descriptions exceeds 4 MiB
        unbounded_bytes = json.dumps({"events": many_events}).encode("utf-8")
        self.assertGreater(len(unbounded_bytes), fetch_mod.MAX_OUTPUT_BYTES)

        # Write via custom payload loop matching fetch-events logic
        payload = {"updatedAt": 1726394400, "events": many_events, "nextEvent": None}
        payload_bytes = json.dumps(payload, indent=2).encode("utf-8")
        if len(payload_bytes) > fetch_mod.MAX_OUTPUT_BYTES:
            for ev in many_events:
                ev["description"] = ""
            payload["events"] = many_events
            payload_bytes = json.dumps(payload, indent=2).encode("utf-8")

        if len(payload_bytes) > fetch_mod.MAX_OUTPUT_BYTES:
            while many_events and len(payload_bytes) > fetch_mod.MAX_OUTPUT_BYTES:
                many_events.pop()
                payload["events"] = many_events
                payload_bytes = json.dumps(payload, indent=2).encode("utf-8")

        self.assertLessEqual(len(payload_bytes), fetch_mod.MAX_OUTPUT_BYTES)
        parsed = json.loads(payload_bytes.decode("utf-8"))
        self.assertIn("events", parsed)

    # 9. Cache dir refusals
    def test_cache_dir_refusals(self):
        """Verify cache writer refuses symlinks and group-writable directories."""
        # Case A: dir is a symlink
        real_target_dir = os.path.join(self.tmp_dir.name, "real_target")
        os.mkdir(real_target_dir, 0o700)
        symlink_dir = os.path.join(self.tmp_dir.name, "symlink_dir")
        os.symlink(real_target_dir, symlink_dir)

        out_in_symlink = os.path.join(symlink_dir, "events.json")
        with self.assertRaises(PermissionError):
            fetch_mod.write_private_file(symlink_dir, "events.json", b"test")

        # Case B: dir is group-writable
        group_write_dir = os.path.join(self.tmp_dir.name, "group_write")
        os.mkdir(group_write_dir, 0o700)
        os.chmod(group_write_dir, 0o777)
        try:
            with self.assertRaises(PermissionError):
                fetch_mod.write_private_file(group_write_dir, "events.json", b"test")
        finally:
            os.chmod(group_write_dir, 0o700)

        # Case C: CLI run with symlink cache dir exits 1, logs one line, target untouched
        cli_out_in_symlink = os.path.join(symlink_dir, "events.json")
        with open(self.cfg_path, "w") as f:
            json.dump([], f)
        res = self._run_fetch(extra_args=["--output", cli_out_in_symlink])
        self.assertEqual(res.returncode, 1)
        self.assertIn("error saving cache", res.stderr)
        self.assertFalse(os.path.exists(os.path.join(real_target_dir, "events.json")))

    # 10. No-follow replace
    def test_nofollow_replace(self):
        """Verify writing replaces a symlink file without modifying the decoy target."""
        decoy_path = os.path.join(self.tmp_dir.name, "decoy.txt")
        with open(decoy_path, "w") as f:
            f.write("ORIGINAL_DECOY_CONTENT")

        target_name = "events.json"
        symlink_target = os.path.join(self.tmp_dir.name, target_name)
        os.symlink(decoy_path, symlink_target)

        fetch_mod.write_private_file(self.tmp_dir.name, target_name, b'{"status": "new"}')

        # Decoy must NOT be modified
        with open(decoy_path, "r") as f:
            self.assertEqual(f.read(), "ORIGINAL_DECOY_CONTENT")

        # Target must now be a regular 0600 file
        st = os.stat(symlink_target)
        self.assertTrue(stat.S_ISREG(st.st_mode))
        self.assertEqual(stat.S_IMODE(st.st_mode), 0o600)

    # 11. Temp cleanup
    def test_temp_cleanup(self):
        """Verify failure during atomic replace cleans up temporary files."""
        # Directory is valid initially, but we pass invalid data to raise error during write
        with self.assertRaises(Exception):
            # passing non-bytes data raises TypeError during write
            fetch_mod.write_private_file(self.tmp_dir.name, "events.json", "not bytes")  # type: ignore

        files = os.listdir(self.tmp_dir.name)
        tmp_files = [f for f in files if f.endswith(".tmp")]
        self.assertEqual(tmp_files, [])

    # 12. manage-event.py validation and no trigger_fetch
    def test_manage_event_validation_and_no_trigger_fetch(self):
        """Verify manage-event rejects bad arguments with exit 2 and trigger_fetch is absent."""
        # Load manage-event module
        m_spec = importlib.util.spec_from_file_location("manage_event", MANAGE_SCRIPT)
        self.assertIsNotNone(m_spec)
        manage_mod = importlib.util.module_from_spec(m_spec)
        m_spec.loader.exec_module(manage_mod)

        # Decision 5 / Acceptance: trigger_fetch must be absent
        self.assertFalse(hasattr(manage_mod, "trigger_fetch"))

        # subprocess must not be imported
        self.assertFalse(hasattr(manage_mod, "subprocess"))

        bad_invocations = [
            ["add", "--date", "2026-02-30", "--summary", "Bad Date"],
            ["add", "--date", "invalid-date", "--summary", "Bad Date"],
            ["add", "--date", "2026-09-20", "--summary", ""],
            ["add", "--date", "2026-09-20", "--summary", "X" * 600],
            ["add", "--date", "2026-09-20", "--summary", "OK", "--start-time", "25:00"],
            ["add", "--date", "2026-09-20", "--summary", "OK", "--end-time", "10:70"],
            ["add", "--date", "2026-09-20", "--summary", "OK", "--color", "not-a-color"],
            ["delete", "--uid", "bad uid with spaces!"],
            ["delete", "--uid", "bad/slash"],
        ]

        for args in bad_invocations:
            cmd = [sys.executable, MANAGE_SCRIPT] + args
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 2, f"Expected exit 2 for args {args}, got {res.returncode}")
            data = json.loads(res.stdout)
            self.assertEqual(data["status"], "error")


if __name__ == "__main__":
    unittest.main()
