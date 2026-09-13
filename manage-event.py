#!/usr/bin/env python3
"""
manage-event.py — Local calendar event manager for fred.clock.

Allows adding, deleting, and listing events in a local RFC 5545 .ics file,
and ensures the local calendar feed is registered in calendars.json.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
import zoneinfo

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/fred.clock/calendars.json")
DEFAULT_ICS_PATH = os.path.expanduser("~/.config/fred.clock/local.ics")
DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/fred.clock/events.json")
FETCH_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch-events.py")


def get_local_tz_name() -> str:
    """Determine the local IANA timezone name."""
    try:
        if os.path.islink("/etc/localtime"):
            real_path = os.path.realpath("/etc/localtime")
            if "zoneinfo/" in real_path:
                return real_path.split("zoneinfo/", 1)[1]
        if os.path.exists("/etc/timezone"):
            with open("/etc/timezone", "r") as f:
                name = f.read().strip()
                if name:
                    return name
    except Exception:
        pass
    try:
        now_tz = datetime.datetime.now().astimezone().tzname()
        if now_tz:
            return now_tz
    except Exception:
        pass
    return "UTC"


def escape_ics_text(text: str) -> str:
    """Escape special characters per RFC 5545."""
    if not text:
        return ""
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return text


def ensure_ics_exists(ics_path: str) -> None:
    """Ensure the .ics file exists with a valid VCALENDAR wrapper."""
    ics_path = os.path.expanduser(ics_path)
    os.makedirs(os.path.dirname(ics_path), exist_ok=True)
    if not os.path.exists(ics_path) or os.path.getsize(ics_path) == 0:
        content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Fred//fred.clock Local Calendar//EN\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "METHOD:PUBLISH\r\n"
            "X-WR-CALNAME:Local Calendar\r\n"
            "END:VCALENDAR\r\n"
        )
        with open(ics_path, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            os.chmod(ics_path, 0o600)
        except Exception:
            pass


def ensure_config_registered(config_path: str, ics_path: str, account: str = "Local", color: str = "#fbbc05") -> bool:
    """Ensure the local .ics feed is present in calendars.json."""
    config_path = os.path.expanduser(config_path)
    ics_path = os.path.expanduser(ics_path)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    feeds = []
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                feeds = json.load(f)
        except Exception:
            feeds = []

    norm_ics = os.path.normpath(ics_path)
    for feed in feeds:
        feed_path = feed.get("path")
        if feed_path:
            if os.path.normpath(os.path.expanduser(feed_path)) == norm_ics:
                return False  # Already registered

    # Append local feed
    feeds.append({
        "account": account,
        "name": "Local Calendar",
        "path": ics_path,
        "color": color,
        "enabled": True
    })

    # Atomic write to config_path
    dir_name = os.path.dirname(config_path)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".json.tmp") as tf:
        json.dump(feeds, tf, indent=2)
        tmp_name = tf.name
    try:
        os.chmod(tmp_name, 0o600)
    except Exception:
        pass
    os.replace(tmp_name, config_path)
    return True


def add_event(
    ics_path: str,
    date_str: str,
    summary: str,
    all_day: bool = False,
    start_time: str = "09:00",
    end_time: str = "10:00",
    location: str = "",
    description: str = "",
    config_path: str = DEFAULT_CONFIG_PATH,
    account: str = "Local",
    color: str = "#fbbc05",
) -> dict:
    """Add a new VEVENT to the specified .ics file and refresh calendars."""
    ensure_ics_exists(ics_path)
    ensure_config_registered(config_path, ics_path, account=account, color=color)

    ics_path = os.path.expanduser(ics_path)
    event_uid = f"{uuid.uuid4()}@fred.clock"
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Date parsing (YYYY-MM-DD)
    parts = [int(p) for p in date_str.split("-")]
    year, month, day = parts[0], parts[1], parts[2]
    target_date = datetime.date(year, month, day)

    vevent_lines = [
        "BEGIN:VEVENT",
        f"UID:{event_uid}",
        f"DTSTAMP:{now_utc}",
        f"CREATED:{now_utc}",
        f"LAST-MODIFIED:{now_utc}",
        f"SUMMARY:{escape_ics_text(summary)}",
    ]

    if location:
        vevent_lines.append(f"LOCATION:{escape_ics_text(location)}")
    if description:
        vevent_lines.append(f"DESCRIPTION:{escape_ics_text(description)}")

    if all_day:
        dtstart_val = target_date.strftime("%Y%m%d")
        next_date = target_date + datetime.timedelta(days=1)
        dtend_val = next_date.strftime("%Y%m%d")
        vevent_lines.append(f"DTSTART;VALUE=DATE:{dtstart_val}")
        vevent_lines.append(f"DTEND;VALUE=DATE:{dtend_val}")
    else:
        tz_name = get_local_tz_name()
        # Parse start_time and end_time (HH:MM)
        s_hours, s_mins = [int(p) for p in start_time.split(":")[:2]]
        e_hours, e_mins = [int(p) for p in end_time.split(":")[:2]]

        start_dt = datetime.datetime(year, month, day, s_hours, s_mins, 0)
        end_dt = datetime.datetime(year, month, day, e_hours, e_mins, 0)
        if end_dt <= start_dt:
            end_dt = start_dt + datetime.timedelta(hours=1)

        dtstart_str = start_dt.strftime("%Y%m%dT%H%M%S")
        dtend_str = end_dt.strftime("%Y%m%dT%H%M%S")

        vevent_lines.append(f"DTSTART;TZID={tz_name}:{dtstart_str}")
        vevent_lines.append(f"DTEND;TZID={tz_name}:{dtend_str}")

    vevent_lines.append("STATUS:CONFIRMED")
    vevent_lines.append("END:VEVENT")

    vevent_block = "\r\n".join(vevent_lines) + "\r\n"

    # Insert before END:VCALENDAR
    with open(ics_path, "r", encoding="utf-8", errors="replace") as f:
        existing = f.read()

    if "END:VCALENDAR" in existing:
        idx = existing.rfind("END:VCALENDAR")
        updated = existing[:idx] + vevent_block + existing[idx:]
    else:
        updated = existing + "\r\n" + vevent_block + "END:VCALENDAR\r\n"

    with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(ics_path), delete=False, suffix=".ics.tmp") as tf:
        tf.write(updated)
        tmp_name = tf.name
    try:
        os.chmod(tmp_name, 0o600)
    except Exception:
        pass
    os.replace(tmp_name, ics_path)

    # Refresh events cache using fetch-events.py if available
    trigger_fetch(config_path)

    return {
        "status": "ok",
        "uid": event_uid,
        "summary": summary,
        "date": date_str,
        "allDay": all_day,
        "startTime": start_time if not all_day else None,
        "endTime": end_time if not all_day else None,
        "location": location,
    }


def delete_event(ics_path: str, event_uid: str, config_path: str = DEFAULT_CONFIG_PATH) -> bool:
    """Delete a VEVENT matching event_uid from the specified .ics file."""
    ics_path = os.path.expanduser(ics_path)
    if not os.path.exists(ics_path):
        return False

    with open(ics_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    new_lines = []
    in_target = False
    current_block = []
    found = False

    for line in lines:
        stripped = line.strip()
        if stripped == "BEGIN:VEVENT":
            in_target = False
            current_block = [line]
        elif current_block:
            current_block.append(line)
            if stripped.startswith("UID:") and stripped[4:].strip() == event_uid.strip():
                in_target = True
            elif stripped == "END:VEVENT":
                if in_target:
                    found = True
                else:
                    new_lines.extend(current_block)
                current_block = []
                in_target = False
        else:
            new_lines.append(line)

    if found:
        with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(ics_path), delete=False, suffix=".ics.tmp") as tf:
            tf.writelines(new_lines)
            tmp_name = tf.name
        try:
            os.chmod(tmp_name, 0o600)
        except Exception:
            pass
        os.replace(tmp_name, ics_path)
        trigger_fetch(config_path)
        return True

    return False


def trigger_fetch(config_path: str) -> None:
    """Run fetch-events.py to update cache immediately."""
    if os.path.exists(FETCH_SCRIPT):
        try:
            subprocess.run([sys.executable, FETCH_SCRIPT, "--config", config_path], capture_output=True, timeout=10)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Manage local events for fred.clock")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add subcommand
    add_p = subparsers.add_parser("add", help="Add a new event")
    add_p.add_argument("--date", required=True, help="Date in YYYY-MM-DD")
    add_p.add_argument("--summary", required=True, help="Event title/summary")
    add_p.add_argument("--all-day", action="store_true", help="All day event")
    add_p.add_argument("--start-time", default="09:00", help="Start time (HH:MM)")
    add_p.add_argument("--end-time", default="10:00", help="End time (HH:MM)")
    add_p.add_argument("--location", default="", help="Event location")
    add_p.add_argument("--description", default="", help="Event description")
    add_p.add_argument("--ics", default=DEFAULT_ICS_PATH, help="Path to local .ics file")
    add_p.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to calendars.json")
    add_p.add_argument("--account", default="Local", help="Account name for local calendar")
    add_p.add_argument("--color", default="#fbbc05", help="Hex color for local calendar")

    # delete subcommand
    del_p = subparsers.add_parser("delete", help="Delete an event by UID")
    del_p.add_argument("--uid", required=True, help="Event UID to delete")
    del_p.add_argument("--ics", default=DEFAULT_ICS_PATH, help="Path to local .ics file")
    del_p.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to calendars.json")

    args = parser.parse_args()

    if args.command == "add":
        result = add_event(
            ics_path=args.ics,
            date_str=args.date,
            summary=args.summary,
            all_day=args.all_day,
            start_time=args.start_time,
            end_time=args.end_time,
            location=args.location,
            description=args.description,
            config_path=args.config,
            account=args.account,
            color=args.color,
        )
        print(json.dumps(result))
    elif args.command == "delete":
        ok = delete_event(ics_path=args.ics, event_uid=args.uid, config_path=args.config)
        print(json.dumps({"status": "ok" if ok else "not_found", "uid": args.uid}))


if __name__ == "__main__":
    main()
