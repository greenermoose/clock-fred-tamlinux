#!/usr/bin/env python3
"""
manage-event.py — Local calendar event manager for fred.clock.

Allows adding, deleting, and listing events in a local RFC 5545 .ics file,
and ensures the local calendar feed is registered in calendars.json.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import re
import sys
import uuid
import zoneinfo

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/fred.clock/calendars.json")
DEFAULT_ICS_PATH = os.path.expanduser("~/.config/fred.clock/local.ics")

# Import helpers and limit constants from sibling fetch-events.py
_FETCH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch-events.py")
_spec = importlib.util.spec_from_file_location("fetch_events", _FETCH_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load fetch-events from {_FETCH_PATH}")
_fetch_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fetch_mod)

write_private_file = _fetch_mod.write_private_file
MAX_SUMMARY = _fetch_mod.MAX_SUMMARY
MAX_LOCATION = _fetch_mod.MAX_LOCATION
MAX_DESCRIPTION = _fetch_mod.MAX_DESCRIPTION
MAX_FEED_BYTES = _fetch_mod.MAX_FEED_BYTES


def get_local_tz_name() -> str:
    """Determine the local IANA timezone name."""
    try:
        if os.path.islink("/etc/localtime"):
            real_path = os.path.realpath("/etc/localtime")
            if "zoneinfo/" in real_path:
                return real_path.split("zoneinfo/", 1)[1]
        if os.path.exists("/etc/timezone"):
            with open("/etc/timezone", "r", encoding="utf-8") as f:
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
    ics_path = os.path.abspath(os.path.expanduser(ics_path))
    if not os.path.exists(ics_path) or os.path.getsize(ics_path) == 0:
        content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Fred//fred.clock Local Calendar//EN\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "METHOD:PUBLISH\r\n"
            "X-WR-CALNAME:Local Calendar\r\n"
            "END:VCALENDAR\r\n"
        ).encode("utf-8")
        write_private_file(os.path.dirname(ics_path), os.path.basename(ics_path), content)


def ensure_config_registered(
    config_path: str,
    ics_path: str,
    account: str = "Local",
    color: str = "#fbbc05",
) -> bool:
    """Ensure the local .ics feed is present in calendars.json."""
    config_path = os.path.abspath(os.path.expanduser(config_path))
    ics_path = os.path.abspath(os.path.expanduser(ics_path))

    feeds = []
    if os.path.exists(config_path):
        try:
            with open(config_path, "rb") as f:
                raw = f.read(MAX_FEED_BYTES + 1)
                if len(raw) <= MAX_FEED_BYTES:
                    loaded = json.loads(raw.decode("utf-8", errors="replace"))
                    if isinstance(loaded, list):
                        feeds = loaded
        except Exception:
            feeds = []

    norm_ics = os.path.normpath(ics_path)
    for feed in feeds:
        feed_path = feed.get("path")
        if feed_path:
            if os.path.normpath(os.path.expanduser(feed_path)) == norm_ics:
                return False  # Already registered

    # Append local feed
    feeds.append(
        {
            "account": account,
            "name": "Local Calendar",
            "path": ics_path,
            "color": color,
            "enabled": True,
        }
    )

    data = json.dumps(feeds, indent=2).encode("utf-8")
    write_private_file(os.path.dirname(config_path), os.path.basename(config_path), data)
    return True


def read_capped_file(path: str) -> str:
    """Read a local file enforcing MAX_FEED_BYTES."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        return ""
    st = os.stat(abs_path)
    if st.st_size > MAX_FEED_BYTES:
        raise ValueError(f"File {path} size ({st.st_size}) exceeds MAX_FEED_BYTES ({MAX_FEED_BYTES})")

    chunks = []
    total_bytes = 0
    with open(abs_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_FEED_BYTES:
                raise ValueError(f"File {path} exceeded MAX_FEED_BYTES ({MAX_FEED_BYTES})")
            chunks.append(chunk)

    return b"".join(chunks).decode("utf-8", errors="replace")


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
    """Add a new VEVENT to the specified .ics file."""
    ensure_ics_exists(ics_path)
    ensure_config_registered(config_path, ics_path, account=account, color=color)

    abs_ics = os.path.abspath(os.path.expanduser(ics_path))
    event_uid = f"{uuid.uuid4()}@fred.clock"
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

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

    existing = read_capped_file(abs_ics)
    if "END:VCALENDAR" in existing:
        idx = existing.rfind("END:VCALENDAR")
        updated = existing[:idx] + vevent_block + existing[idx:]
    else:
        updated = existing + "\r\n" + vevent_block + "END:VCALENDAR\r\n"

    write_private_file(os.path.dirname(abs_ics), os.path.basename(abs_ics), updated.encode("utf-8"))

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
    abs_ics = os.path.abspath(os.path.expanduser(ics_path))
    if not os.path.exists(abs_ics):
        return False

    content = read_capped_file(abs_ics)
    lines = content.splitlines(keepends=True)

    new_lines = []
    in_target = False
    current_block: list[str] = []
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
        data = "".join(new_lines).encode("utf-8")
        write_private_file(os.path.dirname(abs_ics), os.path.basename(abs_ics), data)
        return True

    return False


def validate_args_or_exit(args: argparse.Namespace) -> None:
    """Validate arguments before touching any file. Exit 2 on error with JSON output."""
    errors = []

    if args.command == "add":
        # --date: YYYY-MM-DD and real date
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
            errors.append(f"Invalid date format: {args.date!r}, expected YYYY-MM-DD")
        else:
            try:
                datetime.date.fromisoformat(args.date)
            except ValueError as e:
                errors.append(f"Invalid calendar date: {args.date} ({e})")

        # --summary: non-empty, <= MAX_SUMMARY
        if not args.summary or not args.summary.strip():
            errors.append("Summary cannot be empty")
        elif len(args.summary) > MAX_SUMMARY:
            errors.append(f"Summary exceeds MAX_SUMMARY ({MAX_SUMMARY} chars)")

        # --start-time / --end-time: HH:MM in range
        if not args.all_day:
            for label, val in [("start-time", args.start_time), ("end-time", args.end_time)]:
                if not re.match(r"^\d{2}:\d{2}$", val):
                    errors.append(f"Invalid {label} format: {val!r}, expected HH:MM")
                else:
                    try:
                        h, m = [int(p) for p in val.split(":")]
                        if not (0 <= h <= 23 and 0 <= m <= 59):
                            errors.append(f"Invalid {label}: {val!r} out of range (00:00-23:59)")
                    except ValueError:
                        errors.append(f"Invalid {label}: {val!r}")

        # --location: <= MAX_LOCATION
        if len(args.location) > MAX_LOCATION:
            errors.append(f"Location exceeds MAX_LOCATION ({MAX_LOCATION} chars)")

        # --description: <= MAX_DESCRIPTION
        if len(args.description) > MAX_DESCRIPTION:
            errors.append(f"Description exceeds MAX_DESCRIPTION ({MAX_DESCRIPTION} chars)")

        # --color: ^#[0-9a-fA-F]{6}$
        if not re.match(r"^#[0-9a-fA-F]{6}$", args.color):
            errors.append(f"Invalid color format: {args.color!r}, expected #RRGGBB")

    elif args.command == "delete":
        # --uid: ^[A-Za-z0-9@._-]{1,255}$
        if not re.match(r"^[A-Za-z0-9@._-]{1,255}$", args.uid):
            errors.append(f"Invalid UID format: {args.uid!r}")

    if errors:
        print(json.dumps({"status": "error", "error": "; ".join(errors)}))
        sys.exit(2)


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
    validate_args_or_exit(args)

    try:
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
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
