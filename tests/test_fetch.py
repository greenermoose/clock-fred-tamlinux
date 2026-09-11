#!/usr/bin/env python3
"""
Unit tests for fred.clock fetch-events.py.
Covers recurrence expansion, EXDATE, all-day events, malformed feeds,
and countdown badge computation.
"""

import datetime
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zoneinfo

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(TEST_DIR)
FETCH_SCRIPT = os.path.join(PLUGIN_DIR, "fetch-events.py")
FIXTURES_DIR = os.path.join(TEST_DIR, "fixtures")


class TestFetchEvents(unittest.TestCase):
    def setUp(self):
        self.ny_tz = zoneinfo.ZoneInfo("America/New_York")

    def test_recurring_and_exdate(self):
        """Verify recurring weekly event generates instances and skips EXDATE."""
        # 2026-09-01 is a Tuesday.
        # Next Tuesdays: Sep 1, Sep 8 (EXDATE), Sep 15, Sep 22, Sep 29...
        config_data = [
            {
                "account": "Work",
                "name": "Syncs",
                "path": os.path.join(FIXTURES_DIR, "recurring.ics"),
                "color": "#34a853",
                "enabled": True,
            }
        ]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as cfg:
            json.dump(config_data, cfg)
            cfg_path = cfg.name

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as out:
            out_path = out.name

        try:
            # Set test now to 2026-09-10 12:00:00 EDT (1725984000)
            # Sep 8 was skipped, next occurrence is Sep 15 10:00:00 EDT
            test_dt = datetime.datetime(2026, 9, 10, 12, 0, 0, tzinfo=self.ny_tz)
            test_ts = int(test_dt.timestamp())

            cmd = [
                sys.executable,
                FETCH_SCRIPT,
                "--config", cfg_path,
                "--output", out_path,
                "--now", str(test_ts),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"fetch-events failed: {res.stderr}")

            with open(out_path, "r") as f:
                data = json.load(f)

            events = data["events"]
            summaries = [e["summary"] for e in events]
            start_dates = [e["start"][:10] for e in events]

            # Sep 01 should be present (within 1 day past window)
            # Sep 08 MUST NOT be present due to EXDATE
            self.assertNotIn("2026-09-08", start_dates)
            # Sep 15 MUST be present
            self.assertIn("2026-09-15", start_dates)
            # Sep 22 MUST be present
            self.assertIn("2026-09-22", start_dates)
            self.assertTrue(all(s == "Team Sync" for s in summaries))

            # Verify file mode is 0600
            st = os.stat(out_path)
            mode = stat.S_IMODE(st.st_mode)
            self.assertEqual(mode, 0o600)

        finally:
            if os.path.exists(cfg_path):
                os.unlink(cfg_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_all_day_events(self):
        """Verify all-day event parses correctly and is marked allDay: true."""
        config_data = [
            {
                "account": "Events",
                "name": "Hackathons",
                "path": os.path.join(FIXTURES_DIR, "all_day.ics"),
                "color": "#ea4335",
                "enabled": True,
            }
        ]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as cfg:
            json.dump(config_data, cfg)
            cfg_path = cfg.name

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as out:
            out_path = out.name

        try:
            test_dt = datetime.datetime(2026, 9, 14, 12, 0, 0, tzinfo=self.ny_tz)
            test_ts = int(test_dt.timestamp())

            cmd = [
                sys.executable,
                FETCH_SCRIPT,
                "--config", cfg_path,
                "--output", out_path,
                "--now", str(test_ts),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

            with open(out_path, "r") as f:
                data = json.load(f)

            events = data["events"]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["summary"], "Hackathon Day")
            self.assertTrue(events[0]["allDay"])

            # All-day events should not trigger countdown badge
            self.assertIsNone(data["nextEvent"])

        finally:
            if os.path.exists(cfg_path):
                os.unlink(cfg_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_malformed_feed_resilience(self):
        """Verify malformed feed fails gracefully without blocking good feeds."""
        config_data = [
            {
                "account": "Bad",
                "name": "Broken Feed",
                "path": os.path.join(FIXTURES_DIR, "malformed.ics"),
                "enabled": True,
            },
            {
                "account": "Good",
                "name": "Good Feed",
                "path": os.path.join(FIXTURES_DIR, "all_day.ics"),
                "enabled": True,
            }
        ]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as cfg:
            json.dump(config_data, cfg)
            cfg_path = cfg.name

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as out:
            out_path = out.name

        try:
            test_dt = datetime.datetime(2026, 9, 14, 12, 0, 0, tzinfo=self.ny_tz)
            test_ts = int(test_dt.timestamp())

            cmd = [
                sys.executable,
                FETCH_SCRIPT,
                "--config", cfg_path,
                "--output", out_path,
                "--now", str(test_ts),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

            with open(out_path, "r") as f:
                data = json.load(f)

            # Good feed event still captured
            self.assertEqual(len(data["events"]), 1)
            self.assertEqual(data["events"][0]["summary"], "Hackathon Day")

        finally:
            if os.path.exists(cfg_path):
                os.unlink(cfg_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_next_event_countdown(self):
        """Verify countdown badge calculates correct minutes until event."""
        # Recurring event is at 10:00 EDT on 2026-09-15.
        # If now is 09:48 EDT (12m before), badge should say "Team Sync in 12m"
        config_data = [
            {
                "account": "Work",
                "name": "Syncs",
                "path": os.path.join(FIXTURES_DIR, "recurring.ics"),
                "color": "#34a853",
                "enabled": True,
            }
        ]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as cfg:
            json.dump(config_data, cfg)
            cfg_path = cfg.name

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as out:
            out_path = out.name

        try:
            # 2026-09-15 09:48:00 EDT -> exactly 12 minutes before 10:00:00
            test_dt = datetime.datetime(2026, 9, 15, 9, 48, 0, tzinfo=self.ny_tz)
            test_ts = int(test_dt.timestamp())

            cmd = [
                sys.executable,
                FETCH_SCRIPT,
                "--config", cfg_path,
                "--output", out_path,
                "--now", str(test_ts),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

            with open(out_path, "r") as f:
                data = json.load(f)

            next_ev = data["nextEvent"]
            self.assertIsNotNone(next_ev)
            self.assertEqual(next_ev["summary"], "Team Sync")
            self.assertEqual(next_ev["minutesUntil"], 12)
            self.assertEqual(next_ev["badgeText"], "Team Sync in 12m")

            # Test in-progress: 10:10 EDT (starts at 10:00, ends at 10:30)
            in_prog_dt = datetime.datetime(2026, 9, 15, 10, 10, 0, tzinfo=self.ny_tz)
            cmd_prog = [
                sys.executable,
                FETCH_SCRIPT,
                "--config", cfg_path,
                "--output", out_path,
                "--now", str(int(in_prog_dt.timestamp())),
            ]
            res_prog = subprocess.run(cmd_prog, capture_output=True, text=True)
            self.assertEqual(res_prog.returncode, 0)

            with open(out_path, "r") as f:
                data_prog = json.load(f)

            next_prog = data_prog["nextEvent"]
            self.assertIsNotNone(next_prog)
            self.assertTrue(next_prog["inProgress"])
            self.assertEqual(next_prog["badgeText"], "Team Sync now")

        finally:
            if os.path.exists(cfg_path):
                os.unlink(cfg_path)
            if os.path.exists(out_path):
                os.unlink(out_path)


if __name__ == "__main__":
    unittest.main()
