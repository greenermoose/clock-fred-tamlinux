#!/usr/bin/env python3
"""
fetch-events.py — Background event fetcher for fred.clock.

Fetches iCalendar (.ics) feeds from secret URLs or local files, expands
recurring events (RRULE, EXDATE, RDATE), normalizes timezones, and writes
an atomic JSON cache at ~/.cache/fred.clock/events.json (mode 0600).

Pure Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import os
import re
import sys
import tempfile
import urllib.request
import zoneinfo
from typing import Any

USER_AGENT = "fred.clock/0.1.0 (Omarchy Shell Plugin)"
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/fred.clock/calendars.json")
DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/fred.clock/events.json")


def get_local_timezone() -> datetime.tzinfo:
    """Detect system local timezone using ZoneInfo, falling back to UTC."""
    tz_env = os.environ.get("TZ")
    if tz_env:
        try:
            return zoneinfo.ZoneInfo(tz_env)
        except Exception:
            pass

    try:
        real_path = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in real_path:
            tz_name = real_path.split("zoneinfo/", 1)[1]
            return zoneinfo.ZoneInfo(tz_name)
    except Exception:
        pass

    try:
        if os.path.exists("/etc/timezone"):
            with open("/etc/timezone", "r") as f:
                tz_name = f.read().strip()
                if tz_name:
                    return zoneinfo.ZoneInfo(tz_name)
    except Exception:
        pass

    try:
        local_tz = datetime.datetime.now().astimezone().tzinfo
        if local_tz is not None:
            return local_tz
    except Exception:
        pass
    return datetime.timezone.utc


def unfold_ics(text: str) -> list[str]:
    """Unfold RFC 5545 folded lines (lines preceded by CRLF + space/tab)."""
    unfolded = re.sub(r"\r?\n[ \t]", "", text)
    return [line.strip() for line in unfolded.splitlines() if line.strip()]


def parse_prop_line(line: str) -> tuple[str, dict[str, str], str]:
    """Parse a property line: NAME[;PARAM=VAL...]:VALUE."""
    if ":" not in line:
        return line.upper(), {}, ""
    prop_part, _, val = line.partition(":")
    parts = prop_part.split(";")
    name = parts[0].upper()
    params: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.upper()] = v.strip('"')
    return name, params, val


def parse_datetime(
    val: str, params: dict[str, str], local_tz: datetime.tzinfo
) -> tuple[datetime.datetime, bool]:
    """
    Parse an iCalendar date or date-time string into an aware datetime.
    Returns (dt, is_all_day).
    """
    val = val.strip()
    is_all_day = params.get("VALUE") == "DATE" or len(val) == 8

    if is_all_day:
        # Format: YYYYMMDD
        dt = datetime.datetime.strptime(val[:8], "%Y%m%d")
        dt = dt.replace(tzinfo=local_tz)
        return dt, True

    # Date-time with possible timezone
    tzid = params.get("TZID")
    tz = local_tz
    if tzid:
        try:
            tz = zoneinfo.ZoneInfo(tzid)
        except Exception:
            tz = local_tz

    # Remove any stray characters after seconds
    if val.endswith("Z"):
        clean_val = val[:-1]
        dt = datetime.datetime.strptime(clean_val, "%Y%m%dT%H%M%S")
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        # May be %Y%m%dT%H%M%S
        dt = datetime.datetime.strptime(val[:15], "%Y%m%dT%H%M%S")
        dt = dt.replace(tzinfo=tz)

    return dt, False


def parse_duration(val: str) -> datetime.timedelta:
    """Parse RFC 5545 duration string like PT1H30M, P1D, PT45M."""
    match = re.match(
        r"^([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$",
        val.strip(),
    )
    if not match:
        return datetime.timedelta(hours=1)
    sign = -1 if match.group(1) == "-" else 1
    weeks = int(match.group(2) or 0)
    days = int(match.group(3) or 0)
    hours = int(match.group(4) or 0)
    minutes = int(match.group(5) or 0)
    seconds = int(match.group(6) or 0)
    delta = datetime.timedelta(
        weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds
    )
    return delta if sign == 1 else -delta


def parse_rrule(rrule_str: str) -> dict[str, Any]:
    """Parse RRULE string into key-value map."""
    out: dict[str, Any] = {}
    for part in rrule_str.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.upper()
            if k == "BYDAY":
                out[k] = [d.strip().upper() for d in v.split(",")]
            elif k in ("INTERVAL", "COUNT"):
                try:
                    out[k] = int(v)
                except ValueError:
                    pass
            else:
                out[k] = v
    return out


def unescape_text(text: str) -> str:
    """Unescape iCal escaped characters."""
    return (
        text.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def expand_event(
    event_data: dict[str, Any],
    window_start: datetime.datetime,
    window_end: datetime.datetime,
    local_tz: datetime.tzinfo,
) -> list[dict[str, Any]]:
    """
    Expand a single VEVENT (including recurrence rules) within the time window.
    """
    start_dt: datetime.datetime = event_data["start_dt"]
    is_all_day: bool = event_data["all_day"]
    duration: datetime.timedelta = event_data["duration"]
    rrule: dict[str, Any] | None = event_data.get("rrule")
    exdates: set[datetime.datetime | datetime.date] = event_data.get("exdates", set())

    instances: list[datetime.datetime] = []

    if not rrule:
        # Non-recurring event
        inst_end = start_dt + duration
        if inst_end >= window_start and start_dt <= window_end:
            instances.append(start_dt)
    else:
        freq = rrule.get("FREQ")
        interval = max(1, int(rrule.get("INTERVAL", 1)))
        count = rrule.get("COUNT")
        until_str = rrule.get("UNTIL")
        until_dt: datetime.datetime | None = None
        if until_str:
            try:
                until_dt, _ = parse_datetime(until_str, {}, local_tz)
            except Exception:
                pass

        byday = rrule.get("BYDAY")
        day_map = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

        curr = start_dt
        generated = 0

        if freq == "DAILY":
            while curr <= window_end:
                if until_dt and curr > until_dt:
                    break
                if count is not None and generated >= count:
                    break
                generated += 1
                if curr + duration >= window_start:
                    instances.append(curr)
                curr += datetime.timedelta(days=interval)

        elif freq == "WEEKLY":
            # Determine target days of week
            target_days = [day_map[d[-2:]] for d in byday if d[-2:] in day_map] if byday else [start_dt.weekday()]
            target_days.sort()

            # Start at the beginning of the start week (Monday)
            curr_week_start = (start_dt - datetime.timedelta(days=start_dt.weekday())).date()
            while True:
                for day_idx in target_days:
                    inst_date = curr_week_start + datetime.timedelta(days=day_idx)
                    inst_dt = datetime.datetime.combine(inst_date, start_dt.time(), tzinfo=start_dt.tzinfo)

                    if inst_dt < start_dt:
                        continue
                    if until_dt and inst_dt > until_dt:
                        break
                    if count is not None and generated >= count:
                        break
                    generated += 1
                    if inst_dt > window_end:
                        break
                    if inst_dt + duration >= window_start:
                        instances.append(inst_dt)

                if (count is not None and generated >= count) or (until_dt and inst_dt > until_dt):
                    break
                curr_week_start += datetime.timedelta(weeks=interval)
                if datetime.datetime.combine(curr_week_start, start_dt.time(), tzinfo=start_dt.tzinfo) > window_end:
                    break

        elif freq == "MONTHLY":
            while curr <= window_end:
                if until_dt and curr > until_dt:
                    break
                if count is not None and generated >= count:
                    break
                generated += 1
                if curr + duration >= window_start:
                    instances.append(curr)
                # Next month step
                year = curr.year + (curr.month - 1 + interval) // 12
                month = (curr.month - 1 + interval) % 12 + 1
                day = min(curr.day, 28)  # Safe day clamp
                curr = curr.replace(year=year, month=month, day=day)

        elif freq == "YEARLY":
            while curr <= window_end:
                if until_dt and curr > until_dt:
                    break
                if count is not None and generated >= count:
                    break
                generated += 1
                if curr + duration >= window_start:
                    instances.append(curr)
                curr = curr.replace(year=curr.year + interval)

    expanded: list[dict[str, Any]] = []
    for inst_start in instances:
        # Check EXDATE
        if inst_start in exdates or inst_start.date() in exdates:
            continue
        inst_end = inst_start + duration

        # Convert to local time for clean display / timestamp calculations
        local_start = inst_start.astimezone(local_tz)
        local_end = inst_end.astimezone(local_tz)

        desc = event_data.get("description", "")
        loc = event_data.get("location", "")
        meeting_url = ""
        url_match = re.search(r"https?://(?:meet\.google\.com|[\w-]+\.zoom\.us|teams\.microsoft\.com|[\w-]+\.webex\.com)/[^\s<>'\"`]+", loc + " " + desc)
        if url_match:
            meeting_url = url_match.group(0)
        elif loc.startswith("http://") or loc.startswith("https://"):
            meeting_url = loc

        end_date_for_key = (local_end - datetime.timedelta(seconds=1)) if is_all_day and local_end > local_start else local_end

        expanded.append({
            "id": event_data["id"],
            "summary": event_data["summary"],
            "start": local_start.isoformat(),
            "end": local_end.isoformat(),
            "dateKey": local_start.strftime("%Y-%m-%d"),
            "endDateKey": end_date_for_key.strftime("%Y-%m-%d"),
            "timeStr": "All Day" if is_all_day else f"{local_start.strftime('%H:%M')} – {local_end.strftime('%H:%M')}",
            "startTs": int(local_start.timestamp()),
            "endTs": int(local_end.timestamp()),
            "allDay": is_all_day,
            "location": loc,
            "description": desc,
            "meetingUrl": meeting_url,
        })

    return expanded


def parse_ics_content(
    content: str,
    window_start: datetime.datetime,
    window_end: datetime.datetime,
    local_tz: datetime.tzinfo,
) -> list[dict[str, Any]]:
    """Parse raw iCalendar text and return list of expanded events in the window."""
    lines = unfold_ics(content)
    events: list[dict[str, Any]] = []

    in_vevent = False
    current_event: dict[str, Any] = {}

    for line in lines:
        if line == "BEGIN:VEVENT":
            in_vevent = True
            current_event = {"exdates": set()}
            continue
        elif line == "END:VEVENT":
            in_vevent = False
            if "start_dt" in current_event and current_event.get("status") != "CANCELLED":
                if "duration" not in current_event:
                    if current_event.get("all_day"):
                        current_event["duration"] = datetime.timedelta(days=1)
                    else:
                        current_event["duration"] = datetime.timedelta(hours=1)
                expanded = expand_event(current_event, window_start, window_end, local_tz)
                events.extend(expanded)
            current_event = {}
            continue

        if not in_vevent:
            continue

        prop, params, val = parse_prop_line(line)

        if prop == "UID":
            current_event["id"] = val
        elif prop == "SUMMARY":
            current_event["summary"] = unescape_text(val)
        elif prop == "STATUS":
            current_event["status"] = val.upper()
        elif prop == "LOCATION":
            current_event["location"] = unescape_text(val)
        elif prop == "DESCRIPTION":
            current_event["description"] = unescape_text(val)
        elif prop == "DTSTART":
            try:
                dt, is_all_day = parse_datetime(val, params, local_tz)
                current_event["start_dt"] = dt
                current_event["all_day"] = is_all_day
            except Exception:
                pass
        elif prop == "DTEND":
            try:
                dt, _ = parse_datetime(val, params, local_tz)
                current_event["end_dt"] = dt
                if "start_dt" in current_event:
                    current_event["duration"] = dt - current_event["start_dt"]
            except Exception:
                pass
        elif prop == "DURATION":
            current_event["duration"] = parse_duration(val)
        elif prop == "RRULE":
            current_event["rrule"] = parse_rrule(val)
        elif prop == "EXDATE":
            # May contain comma-separated datetimes
            for part in val.split(","):
                try:
                    dt, is_date = parse_datetime(part.strip(), params, local_tz)
                    if is_date:
                        current_event["exdates"].add(dt.date())
                    else:
                        current_event["exdates"].add(dt)
                except Exception:
                    pass

    return events


def fetch_feed(feed_info: dict[str, Any], window_start: datetime.datetime, window_end: datetime.datetime, local_tz: datetime.tzinfo) -> list[dict[str, Any]]:
    """Fetch and parse one calendar feed (remote URL or local path)."""
    if not feed_info.get("enabled", True):
        return []

    account = feed_info.get("account", "Personal")
    cal_name = feed_info.get("name", "Calendar")
    color = feed_info.get("color", "#4285f4")
    url = feed_info.get("url")
    path = feed_info.get("path")

    content = ""
    try:
        if url:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8", errors="replace")
        elif path:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                with open(expanded_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
    except Exception as e:
        print(f"fetch-events: failed to fetch feed '{cal_name}': {e}", file=sys.stderr)
        return []

    if not content:
        return []

    try:
        raw_events = parse_ics_content(content, window_start, window_end, local_tz)
        for ev in raw_events:
            ev["account"] = account
            ev["calendar"] = cal_name
            ev["color"] = color
            ev["isLocal"] = bool(path)
            if path:
                ev["localPath"] = os.path.expanduser(path)
        return raw_events
    except Exception as e:
        print(f"fetch-events: error parsing feed '{cal_name}': {e}", file=sys.stderr)
        return []


def compute_next_event(events: list[dict[str, Any]], now_ts: int, badge_minutes: int = 60) -> dict[str, Any] | None:
    """Find the next upcoming or in-progress event for the countdown badge."""
    upcoming = []
    for ev in events:
        if ev.get("allDay", False):
            continue
        start_ts = ev["startTs"]
        end_ts = ev["endTs"]
        # In-progress event
        if start_ts <= now_ts < end_ts:
            upcoming.append((start_ts, ev, 0, True))
        # Future event starting within badge window
        elif start_ts > now_ts:
            diff_min = int((start_ts - now_ts) / 60)
            if badge_minutes <= 0 or diff_min <= badge_minutes:
                upcoming.append((start_ts, ev, diff_min, False))

    if not upcoming:
        return None

    # Sort by start time
    upcoming.sort(key=lambda x: x[0])
    _, next_ev, diff_min, in_progress = upcoming[0]

    summary = next_ev.get("summary", "Event")
    if in_progress:
        badge_text = f"{summary} now"
    elif diff_min <= 0:
        badge_text = f"{summary} now"
    else:
        badge_text = f"{summary} in {diff_min}m"

    return {
        "summary": summary,
        "start": next_ev["start"],
        "end": next_ev["end"],
        "startTs": next_ev["startTs"],
        "endTs": next_ev["endTs"],
        "minutesUntil": diff_min if not in_progress else 0,
        "inProgress": in_progress,
        "badgeText": badge_text,
        "color": next_ev.get("color", "#4285f4"),
        "account": next_ev.get("account", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and cache calendar events for fred.clock")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to calendars.json")
    parser.add_argument("--output", default=DEFAULT_CACHE_PATH, help="Path to write events.json cache")
    parser.add_argument("--badge-minutes", type=int, default=60, help="Max minutes ahead for countdown badge")
    parser.add_argument("--print", action="store_true", help="Print payload to stdout instead of writing file")
    parser.add_argument("--now", type=int, default=None, help="Override current epoch timestamp for testing")

    args = parser.parse_args()

    local_tz = get_local_timezone()
    now_ts = args.now if args.now is not None else int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    now_dt = datetime.datetime.fromtimestamp(now_ts, tz=local_tz)

    # Window: past 1 day to next 30 days
    window_start = now_dt - datetime.timedelta(days=1)
    window_end = now_dt + datetime.timedelta(days=30)

    # Load configuration
    feeds: list[dict[str, Any]] = []
    if os.path.exists(args.config):
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                feeds = json.load(f)
        except Exception as e:
            print(f"fetch-events: failed to read config {args.config}: {e}", file=sys.stderr)

    all_events: list[dict[str, Any]] = []
    if feeds:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(feeds), 8)) as executor:
            futures = [executor.submit(fetch_feed, feed, window_start, window_end, local_tz) for feed in feeds]
            for future in concurrent.futures.as_completed(futures):
                try:
                    feed_events = future.result()
                    all_events.extend(feed_events)
                except Exception as e:
                    print(f"fetch-events: feed worker failed: {e}", file=sys.stderr)

    # Sort events chronologically
    all_events.sort(key=lambda x: (x["startTs"], x.get("summary", "")))

    next_event = compute_next_event(all_events, now_ts, badge_minutes=args.badge_minutes)

    payload = {
        "updatedAt": now_ts,
        "events": all_events,
        "nextEvent": next_event,
    }

    if args.print:
        print(json.dumps(payload, indent=2))
        return 0

    # Write cache atomically with 0600 permissions
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, mode=0o700, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="events-", suffix=".json.tmp", dir=out_dir)
    try:
        os.fchmod(tmp_fd, 0o600)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, args.output)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        print(f"fetch-events: error saving cache to {args.output}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
