#!/usr/bin/env python3
"""
Unit tests for fred.clock manage-event.py.
"""

import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zoneinfo

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(TESTS_DIR)
MANAGE_SCRIPT = os.path.join(PLUGIN_DIR, "manage-event.py")
FETCH_SCRIPT = os.path.join(PLUGIN_DIR, "fetch-events.py")


class TestManageEvent(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.ics_path = os.path.join(self.tmp_dir.name, "local.ics")
        self.config_path = os.path.join(self.tmp_dir.name, "calendars.json")
        self.output_path = os.path.join(self.tmp_dir.name, "events.json")

        with open(self.config_path, "w") as f:
            json.dump([], f)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_add_all_day_event(self):
        """Verify adding an all-day event creates the .ics and registers config."""
        cmd = [
            sys.executable,
            MANAGE_SCRIPT,
            "add",
            "--date", "2026-09-20",
            "--summary", "Birthday Party",
            "--all-day",
            "--location", "City Park",
            "--ics", self.ics_path,
            "--config", self.config_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["summary"], "Birthday Party")
        self.assertTrue(data["allDay"])

        # Check .ics content
        with open(self.ics_path, "r") as f:
            ics_content = f.read()
        self.assertIn("BEGIN:VCALENDAR", ics_content)
        self.assertIn("SUMMARY:Birthday Party", ics_content)
        self.assertIn("DTSTART;VALUE=DATE:20260920", ics_content)
        self.assertIn("DTEND;VALUE=DATE:20260921", ics_content)
        self.assertIn("LOCATION:City Park", ics_content)
        self.assertIn("END:VCALENDAR", ics_content)

        # Check config registered
        with open(self.config_path, "r") as f:
            cfg = json.load(f)
        self.assertEqual(len(cfg), 1)
        self.assertEqual(cfg[0]["account"], "Local")
        self.assertEqual(cfg[0]["path"], self.ics_path)

    def test_add_timed_event(self):
        """Verify adding a timed event generates correct DTSTART/DTEND with TZID."""
        cmd = [
            sys.executable,
            MANAGE_SCRIPT,
            "add",
            "--date", "2026-09-21",
            "--summary", "Dentist Appointment",
            "--start-time", "14:30",
            "--end-time", "15:30",
            "--location", "Main St Dental",
            "--ics", self.ics_path,
            "--config", self.config_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "ok")
        self.assertFalse(data["allDay"])

        with open(self.ics_path, "r") as f:
            ics_content = f.read()
        self.assertIn("SUMMARY:Dentist Appointment", ics_content)
        self.assertIn("20260921T143000", ics_content)
        self.assertIn("20260921T153000", ics_content)

    def test_delete_event(self):
        """Verify deleting an event by UID removes it from the .ics file."""
        # Add two events
        cmd1 = [
            sys.executable,
            MANAGE_SCRIPT,
            "add",
            "--date", "2026-09-22",
            "--summary", "First Event",
            "--all-day",
            "--ics", self.ics_path,
            "--config", self.config_path,
        ]
        res1 = subprocess.run(cmd1, capture_output=True, text=True)
        data1 = json.loads(res1.stdout)
        uid1 = data1["uid"]

        cmd2 = [
            sys.executable,
            MANAGE_SCRIPT,
            "add",
            "--date", "2026-09-23",
            "--summary", "Second Event",
            "--all-day",
            "--ics", self.ics_path,
            "--config", self.config_path,
        ]
        res2 = subprocess.run(cmd2, capture_output=True, text=True)
        data2 = json.loads(res2.stdout)
        uid2 = data2["uid"]

        # Delete first event
        del_cmd = [
            sys.executable,
            MANAGE_SCRIPT,
            "delete",
            "--uid", uid1,
            "--ics", self.ics_path,
            "--config", self.config_path,
        ]
        del_res = subprocess.run(del_cmd, capture_output=True, text=True)
        self.assertEqual(del_res.returncode, 0)
        del_data = json.loads(del_res.stdout)
        self.assertEqual(del_data["status"], "ok")

        with open(self.ics_path, "r") as f:
            content = f.read()
        self.assertNotIn("First Event", content)
        self.assertIn("Second Event", content)


if __name__ == "__main__":
    unittest.main()
