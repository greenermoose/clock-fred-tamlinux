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
import resource
import signal
import stat
import sys
import time
import urllib.parse
import urllib.request
import zoneinfo
from typing import Any, Iterator

USER_AGENT = "fred.clock/1.3.0 (Omarchy Shell Plugin)"
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/fred.clock/calendars.json")
DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/fred.clock/events.json")

# Limits as defined in §5
MAX_CONFIG_BYTES = 64 * 1024  # 64 KiB
MAX_FEEDS = 32
MAX_FEED_BYTES = 8 * 1024 * 1024  # 8 MiB
FEED_DEADLINE_S = 20  # seconds
MAX_LINE_BYTES = 64 * 1024  # 64 KiB
MAX_LINES = 200_000
MAX_VEVENTS_PER_FEED = 20_000
MAX_EXDATES = 2_000
MAX_INSTANCES_PER_EVENT = 1_000
INTERVAL_MIN = 1
INTERVAL_MAX = 366
COUNT_MIN = 1
COUNT_MAX = 10_000
MAX_SUMMARY = 512
MAX_LOCATION = 2_048
MAX_DESCRIPTION = 4_096
MAX_EVENTS_TOTAL = 5_000
MAX_OUTPUT_BYTES = 4 * 1024 * 1024  # 4 MiB
DEADLINE_S = 45
RLIMIT_CPU_SOFT = 30
RLIMIT_CPU_HARD = 35
RLIMIT_AS_BYTES = 512 * 1024 * 1024  # 512 MiB
RLIMIT_FSIZE_BYTES = 16 * 1024 * 1024  # 16 MiB
RLIMIT_NOFILE_COUNT = 64


def write_private_file(directory: str, name: str, data: bytes) -> None:
    """Atomically replace <directory>/<name> using only descriptor-relative,
    no-follow operations. Refuses a directory that is not a private,
    self-owned directory; creates it 0700 if absent."""
    if not name or os.path.basename(name) != name or name in (".", ".."):
        raise ValueError(f"Target name must be a single path component, got: {name!r}")

    directory = os.path.abspath(directory)
    parent = os.path.dirname(directory)

    # Validate / create parent directory (~/.cache or ~/.config)
    if not os.path.exists(parent):
        os.makedirs(parent, mode=0o700, exist_ok=True)

    try:
        pfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError as e:
        raise PermissionError(f"Cannot open parent directory {parent}: {e}")

    try:
        pst = os.fstat(pfd)
        if not stat.S_ISDIR(pst.st_mode):
            raise PermissionError(f"Parent {parent} is not a directory")
        # Refuse if group/other-writable and not sticky
        if (pst.st_mode & 0o022) != 0 and not (pst.st_mode & stat.S_ISVTX):
            raise PermissionError(
                f"Parent directory {parent} is group/other writable without sticky bit (mode {oct(pst.st_mode)})"
            )
    finally:
        os.close(pfd)

    # Ensure target directory exists
    try:
        os.mkdir(directory, 0o700)
    except FileExistsError:
        pass

    try:
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as e:
        raise PermissionError(f"Cannot open directory {directory} safely (symlink or error): {e}")

    tmp_name = None
    try:
        st = os.fstat(dfd)
        if not stat.S_ISDIR(st.st_mode):
            raise PermissionError(f"{directory} is not a directory")
        if st.st_uid != os.getuid():
            raise PermissionError(f"{directory} is not owned by current user (uid {st.st_uid} != {os.getuid()})")
        if (st.st_mode & 0o022) != 0:
            raise PermissionError(f"{directory} has insecure permissions (mode {oct(st.st_mode)})")

        token = os.urandom(8).hex()
        tmp_name = f".{name}.{token}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        tfd = os.open(tmp_name, flags, 0o600, dir_fd=dfd)
        try:
            total_written = 0
            while total_written < len(data):
                n = os.write(tfd, data[total_written:])
                if n == 0:
                    raise OSError("Zero bytes written to temporary file")
                total_written += n
            os.fsync(tfd)
        finally:
            os.close(tfd)

        os.rename(tmp_name, name, src_dir_fd=dfd, dst_dir_fd=dfd)
        tmp_name = None
        os.fsync(dfd)
    except Exception:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name, dir_fd=dfd)
            except OSError:
                pass
        raise
    finally:
        os.close(dfd)


class _HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    """HTTP redirect handler refusing non-HTTPS redirects and capping hops at 5."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme.lower() != "https":
            raise ValueError(f"Insecure redirect to non-https URL: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

    def http_error_302(self, req: Any, fp: Any, code: int, msg: str, headers: Any) -> Any:
        hops = getattr(req, "_redirect_hops", 0) + 1
        if hops > 5:
            raise ValueError("Too many redirects (max 5)")
        req._redirect_hops = hops
        return super().http_error_302(req, fp, code, msg, headers)

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


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


def unfold_ics(text: str) -> Iterator[str]:
    """Yield unfolded RFC 5545 lines, capped by MAX_LINE_BYTES and MAX_LINES."""
    current_line = ""
    line_count = 0
    for raw_line in text.splitlines():
        if raw_line.startswith(" ") or raw_line.startswith("\t"):
            addition = raw_line[1:]
            if len((current_line + addition).encode("utf-8")) > MAX_LINE_BYTES:
                print(
                    f"fetch-events: warning: line exceeded MAX_LINE_BYTES ({MAX_LINE_BYTES})",
                    file=sys.stderr,
                )
                continue
            current_line += addition
        else:
            if current_line.strip():
                yield current_line.strip()
                line_count += 1
                if line_count >= MAX_LINES:
                    print(
                        f"fetch-events: warning: feed reached MAX_LINES ({MAX_LINES})",
                        file=sys.stderr,
                    )
                    return
            current_line = raw_line
            if len(current_line.encode("utf-8")) > MAX_LINE_BYTES:
                print(
                    f"fetch-events: warning: line exceeded MAX_LINE_BYTES ({MAX_LINE_BYTES})",
                    file=sys.stderr,
                )
                current_line = current_line.encode("utf-8")[:MAX_LINE_BYTES].decode("utf-8", errors="ignore")
    if current_line.strip():
        yield current_line.strip()


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
        dt = datetime.datetime.strptime(val[:8], "%Y%m%d")
        dt = dt.replace(tzinfo=local_tz)
        return dt, True

    tzid = params.get("TZID")
    tz = local_tz
    if tzid:
        try:
            tz = zoneinfo.ZoneInfo(tzid)
        except Exception:
            tz = local_tz

    if val.endswith("Z"):
        clean_val = val[:-1]
        dt = datetime.datetime.strptime(clean_val, "%Y%m%dT%H%M%S")
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
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
    """Parse RRULE string into key-value map with clamped parameters."""
    out: dict[str, Any] = {}
    for part in rrule_str.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.upper()
            if k == "BYDAY":
                out[k] = [d.strip().upper() for d in v.split(",")]
            elif k == "INTERVAL":
                try:
                    val_int = int(v)
                    out[k] = max(INTERVAL_MIN, min(val_int, INTERVAL_MAX))
                except (ValueError, TypeError):
                    out[k] = 1
            elif k == "COUNT":
                try:
                    val_int = int(v)
                    out[k] = max(COUNT_MIN, min(val_int, COUNT_MAX))
                except (ValueError, TypeError):
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
    Guarded by MAX_INSTANCES_PER_EVENT iterations.
    """
    start_dt: datetime.datetime = event_data["start_dt"]
    is_all_day: bool = event_data["all_day"]
    duration: datetime.timedelta = event_data["duration"]
    rrule: dict[str, Any] | None = event_data.get("rrule")
    exdates: set[datetime.datetime | datetime.date] = event_data.get("exdates", set())

    instances: list[datetime.datetime] = []

    if not rrule:
        inst_end = start_dt + duration
        if inst_end >= window_start and start_dt <= window_end:
            instances.append(start_dt)
    else:
        freq = rrule.get("FREQ")
        try:
            raw_interval = int(rrule.get("INTERVAL", 1))
        except (ValueError, TypeError):
            raw_interval = 1
        interval = max(INTERVAL_MIN, min(raw_interval, INTERVAL_MAX))

        count = None
        if "COUNT" in rrule:
            try:
                raw_count = int(rrule["COUNT"])
                count = max(COUNT_MIN, min(raw_count, COUNT_MAX))
            except (ValueError, TypeError):
                count = None

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
        iteration_count = 0

        if freq == "DAILY":
            while curr <= window_end and iteration_count < MAX_INSTANCES_PER_EVENT:
                iteration_count += 1
                if until_dt and curr > until_dt:
                    break
                if count is not None and generated >= count:
                    break
                generated += 1
                if curr + duration >= window_start:
                    instances.append(curr)
                curr += datetime.timedelta(days=interval)

        elif freq == "WEEKLY":
            target_days = (
                [day_map[d[-2:]] for d in byday if d[-2:] in day_map]
                if byday
                else [start_dt.weekday()]
            )
            target_days.sort()

            curr_week_start = (start_dt - datetime.timedelta(days=start_dt.weekday())).date()
            while curr_week_start <= window_end.date() and iteration_count < MAX_INSTANCES_PER_EVENT:
                for day_idx in target_days:
                    iteration_count += 1
                    if iteration_count > MAX_INSTANCES_PER_EVENT:
                        break
                    inst_date = curr_week_start + datetime.timedelta(days=day_idx)
                    inst_dt = datetime.datetime.combine(
                        inst_date, start_dt.time(), tzinfo=start_dt.tzinfo
                    )

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

                if (
                    (count is not None and generated >= count)
                    or (until_dt and inst_dt > until_dt)
                    or iteration_count >= MAX_INSTANCES_PER_EVENT
                ):
                    break
                curr_week_start += datetime.timedelta(weeks=interval)

        elif freq == "MONTHLY":
            while curr <= window_end and iteration_count < MAX_INSTANCES_PER_EVENT:
                iteration_count += 1
                if until_dt and curr > until_dt:
                    break
                if count is not None and generated >= count:
                    break
                generated += 1
                if curr + duration >= window_start:
                    instances.append(curr)
                year = curr.year + (curr.month - 1 + interval) // 12
                month = (curr.month - 1 + interval) % 12 + 1
                day = min(curr.day, 28)
                curr = curr.replace(year=year, month=month, day=day)

        elif freq == "YEARLY":
            while curr <= window_end and iteration_count < MAX_INSTANCES_PER_EVENT:
                iteration_count += 1
                if until_dt and curr > until_dt:
                    break
                if count is not None and generated >= count:
                    break
                generated += 1
                if curr + duration >= window_start:
                    instances.append(curr)
                try:
                    curr = curr.replace(year=curr.year + interval)
                except ValueError:
                    break

    expanded: list[dict[str, Any]] = []
    for inst_start in instances:
        if inst_start in exdates or inst_start.date() in exdates:
            continue
        inst_end = inst_start + duration

        local_start = inst_start.astimezone(local_tz)
        local_end = inst_end.astimezone(local_tz)

        desc = event_data.get("description", "")
        loc = event_data.get("location", "")
        meeting_url = ""
        url_match = re.search(
            r"https?://(?:meet\.google\.com|[\w-]+\.zoom\.us|teams\.microsoft\.com|[\w-]+\.webex\.com)/[^\s<>'\"`]+",
            loc + " " + desc,
        )
        if url_match:
            meeting_url = url_match.group(0)
        elif loc.startswith("http://") or loc.startswith("https://"):
            meeting_url = loc

        end_date_for_key = (
            (local_end - datetime.timedelta(seconds=1))
            if is_all_day and local_end > local_start
            else local_end
        )

        expanded.append(
            {
                "id": event_data["id"],
                "summary": event_data["summary"],
                "start": local_start.isoformat(),
                "end": local_end.isoformat(),
                "dateKey": local_start.strftime("%Y-%m-%d"),
                "endDateKey": end_date_for_key.strftime("%Y-%m-%d"),
                "timeStr": (
                    "All Day"
                    if is_all_day
                    else f"{local_start.strftime('%H:%M')} – {local_end.strftime('%H:%M')}"
                ),
                "startTs": int(local_start.timestamp()),
                "endTs": int(local_end.timestamp()),
                "allDay": is_all_day,
                "location": loc,
                "description": desc,
                "meetingUrl": meeting_url,
            }
        )

    return expanded


def parse_ics_content(
    content: str,
    window_start: datetime.datetime,
    window_end: datetime.datetime,
    local_tz: datetime.tzinfo,
) -> list[dict[str, Any]]:
    """Parse raw iCalendar text and return list of expanded events in the window."""
    events: list[dict[str, Any]] = []

    in_vevent = False
    current_event: dict[str, Any] = {}
    vevent_count = 0

    for line in unfold_ics(content):
        if line == "BEGIN:VEVENT":
            vevent_count += 1
            if vevent_count > MAX_VEVENTS_PER_FEED:
                print(
                    f"fetch-events: warning: feed reached MAX_VEVENTS_PER_FEED ({MAX_VEVENTS_PER_FEED})",
                    file=sys.stderr,
                )
                break
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
            current_event["id"] = val[:255]
        elif prop == "SUMMARY":
            current_event["summary"] = unescape_text(val[:MAX_SUMMARY])
        elif prop == "STATUS":
            current_event["status"] = val.upper()
        elif prop == "LOCATION":
            current_event["location"] = unescape_text(val[:MAX_LOCATION])
        elif prop == "DESCRIPTION":
            current_event["description"] = unescape_text(val[:MAX_DESCRIPTION])
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
            for part in val.split(","):
                if len(current_event["exdates"]) >= MAX_EXDATES:
                    break
                try:
                    dt, is_date = parse_datetime(part.strip(), params, local_tz)
                    if is_date:
                        current_event["exdates"].add(dt.date())
                    else:
                        current_event["exdates"].add(dt)
                except Exception:
                    pass

    return events


def fetch_feed(
    feed_info: dict[str, Any],
    window_start: datetime.datetime,
    window_end: datetime.datetime,
    local_tz: datetime.tzinfo,
) -> list[dict[str, Any]]:
    """Fetch and parse one calendar feed (remote HTTPS URL or local path)."""
    if not feed_info.get("enabled", True):
        return []

    account = str(feed_info.get("account", "Personal"))[:128]
    cal_name = str(feed_info.get("name", "Calendar"))[:128]
    color = str(feed_info.get("color", "#4285f4"))
    if not re.match(r"^#[0-9a-fA-F]{6}$", color):
        color = "#4285f4"

    url = feed_info.get("url")
    path = feed_info.get("path")

    content = ""
    try:
        if url:
            raw_url = str(url)
            if raw_url.startswith("webcal://"):
                raw_url = "https://" + raw_url[len("webcal://"):]
            parsed_u = urllib.parse.urlparse(raw_url)
            if parsed_u.scheme.lower() != "https":
                print(f"fetch-events: refusing non-HTTPS feed URL: {raw_url}", file=sys.stderr)
                return []

            opener = urllib.request.build_opener(_HttpsOnlyRedirect())
            req = urllib.request.Request(raw_url, headers={"User-Agent": USER_AGENT})
            with opener.open(req, timeout=10) as response:
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        if int(content_length) > MAX_FEED_BYTES:
                            print(
                                f"fetch-events: feed '{cal_name}' Content-Length ({content_length}) exceeds MAX_FEED_BYTES ({MAX_FEED_BYTES})",
                                file=sys.stderr,
                            )
                            return []
                    except ValueError:
                        pass

                start_time = time.monotonic()
                chunks = []
                total_bytes = 0
                while True:
                    if time.monotonic() - start_time > FEED_DEADLINE_S:
                        print(
                            f"fetch-events: feed '{cal_name}' exceeded FEED_DEADLINE_S ({FEED_DEADLINE_S}s)",
                            file=sys.stderr,
                        )
                        return []
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > MAX_FEED_BYTES:
                        print(
                            f"fetch-events: feed '{cal_name}' exceeded MAX_FEED_BYTES ({MAX_FEED_BYTES})",
                            file=sys.stderr,
                        )
                        return []
                    chunks.append(chunk)

                content = b"".join(chunks).decode("utf-8", errors="replace")

        elif path:
            expanded_path = os.path.expanduser(str(path))
            if os.path.exists(expanded_path):
                with open(expanded_path, "rb") as f:
                    st = os.fstat(f.fileno())
                    if not stat.S_ISREG(st.st_mode):
                        print(
                            f"fetch-events: local feed '{cal_name}' is not a regular file",
                            file=sys.stderr,
                        )
                        return []
                    if st.st_uid != os.getuid():
                        print(
                            f"fetch-events: local feed '{cal_name}' is not owned by current user",
                            file=sys.stderr,
                        )
                        return []
                    if st.st_size > MAX_FEED_BYTES:
                        print(
                            f"fetch-events: local feed '{cal_name}' size ({st.st_size}) exceeds MAX_FEED_BYTES ({MAX_FEED_BYTES})",
                            file=sys.stderr,
                        )
                        return []

                    chunks = []
                    total_bytes = 0
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        if total_bytes > MAX_FEED_BYTES:
                            print(
                                f"fetch-events: local feed '{cal_name}' exceeded MAX_FEED_BYTES ({MAX_FEED_BYTES})",
                                file=sys.stderr,
                            )
                            return []
                        chunks.append(chunk)
                    content = b"".join(chunks).decode("utf-8", errors="replace")
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
                ev["localPath"] = os.path.expanduser(str(path))
        return raw_events
    except Exception as e:
        print(f"fetch-events: error parsing feed '{cal_name}': {e}", file=sys.stderr)
        return []


def compute_next_event(
    events: list[dict[str, Any]], now_ts: int, badge_minutes: int = 60
) -> dict[str, Any] | None:
    """Find the next upcoming or in-progress event for the countdown badge."""
    upcoming = []
    for ev in events:
        if ev.get("allDay", False):
            continue
        start_ts = ev["startTs"]
        end_ts = ev["endTs"]
        if start_ts <= now_ts < end_ts:
            upcoming.append((start_ts, ev, 0, True))
        elif start_ts > now_ts:
            diff_min = int((start_ts - now_ts) / 60)
            if badge_minutes <= 0 or diff_min <= badge_minutes:
                upcoming.append((start_ts, ev, diff_min, False))

    if not upcoming:
        return None

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
    parser.add_argument("--deadline", type=int, default=DEADLINE_S, help="Self-imposed alarm deadline in seconds")
    parser.add_argument("--no-rlimits", action="store_true", help="Disable resource rlimits")

    args = parser.parse_args()

    # Self-supervision at the top of main()
    if not args.no_rlimits:
        rlimits_to_set = [
            ("RLIMIT_CPU", resource.RLIMIT_CPU, (RLIMIT_CPU_SOFT, RLIMIT_CPU_HARD)),
            ("RLIMIT_AS", resource.RLIMIT_AS, (RLIMIT_AS_BYTES, RLIMIT_AS_BYTES)),
            ("RLIMIT_FSIZE", resource.RLIMIT_FSIZE, (RLIMIT_FSIZE_BYTES, RLIMIT_FSIZE_BYTES)),
            ("RLIMIT_NOFILE", resource.RLIMIT_NOFILE, (RLIMIT_NOFILE_COUNT, RLIMIT_NOFILE_COUNT)),
        ]
        for name, res_type, limits in rlimits_to_set:
            try:
                resource.setrlimit(res_type, limits)
            except Exception as e:
                print(f"fetch-events: warning: failed to set {name}: {e}", file=sys.stderr)

    if args.deadline and args.deadline > 0:
        try:
            signal.alarm(args.deadline)
        except Exception as e:
            print(f"fetch-events: warning: failed to set alarm: {e}", file=sys.stderr)

    local_tz = get_local_timezone()
    now_ts = (
        args.now
        if args.now is not None
        else int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    )
    now_dt = datetime.datetime.fromtimestamp(now_ts, tz=local_tz)

    # Window: past 1 day to next 30 days
    window_start = now_dt - datetime.timedelta(days=1)
    window_end = now_dt + datetime.timedelta(days=30)

    # Load configuration with bounds
    feeds: list[dict[str, Any]] = []
    if os.path.exists(args.config):
        try:
            with open(args.config, "rb") as f:
                st = os.fstat(f.fileno())
                if not stat.S_ISREG(st.st_mode):
                    print(f"fetch-events: config {args.config} is not a regular file", file=sys.stderr)
                elif st.st_uid != os.getuid():
                    print(f"fetch-events: config {args.config} is not owned by current user", file=sys.stderr)
                elif st.st_size > MAX_CONFIG_BYTES:
                    print(
                        f"fetch-events: config {args.config} size ({st.st_size}) exceeds MAX_CONFIG_BYTES ({MAX_CONFIG_BYTES})",
                        file=sys.stderr,
                    )
                else:
                    raw_cfg = f.read(MAX_CONFIG_BYTES + 1)
                    if len(raw_cfg) > MAX_CONFIG_BYTES:
                        print(
                            f"fetch-events: config exceeds MAX_CONFIG_BYTES ({MAX_CONFIG_BYTES})",
                            file=sys.stderr,
                        )
                    else:
                        loaded = json.loads(raw_cfg.decode("utf-8", errors="replace"))
                        if not isinstance(loaded, list):
                            print("fetch-events: config must be a JSON list", file=sys.stderr)
                        else:
                            if len(loaded) > MAX_FEEDS:
                                print(
                                    f"fetch-events: config feeds ({len(loaded)}) exceeds MAX_FEEDS ({MAX_FEEDS}), truncating",
                                    file=sys.stderr,
                                )
                                loaded = loaded[:MAX_FEEDS]
                            for raw_feed in loaded:
                                if not isinstance(raw_feed, dict):
                                    continue
                                validated_feed = {
                                    "enabled": bool(raw_feed.get("enabled", True)),
                                    "account": str(raw_feed.get("account", "Personal"))[:128],
                                    "name": str(raw_feed.get("name", "Calendar"))[:128],
                                }
                                color = str(raw_feed.get("color", "#4285f4"))
                                if not re.match(r"^#[0-9a-fA-F]{6}$", color):
                                    color = "#4285f4"
                                validated_feed["color"] = color

                                if "url" in raw_feed:
                                    raw_url = str(raw_feed["url"])
                                    if raw_url.startswith("webcal://"):
                                        raw_url = "https://" + raw_url[len("webcal://"):]
                                    parsed_u = urllib.parse.urlparse(raw_url)
                                    if parsed_u.scheme.lower() != "https":
                                        print(
                                            f"fetch-events: refusing non-HTTPS feed URL: {raw_url}",
                                            file=sys.stderr,
                                        )
                                        continue
                                    validated_feed["url"] = raw_url

                                if "path" in raw_feed:
                                    validated_feed["path"] = str(raw_feed["path"])

                                feeds.append(validated_feed)
        except Exception as e:
            print(f"fetch-events: failed to read config {args.config}: {e}", file=sys.stderr)

    all_events: list[dict[str, Any]] = []
    if feeds:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(feeds), 8)) as executor:
            futures = [
                executor.submit(fetch_feed, feed, window_start, window_end, local_tz)
                for feed in feeds
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    feed_events = future.result()
                    all_events.extend(feed_events)
                except Exception as e:
                    print(f"fetch-events: feed worker failed: {e}", file=sys.stderr)

    # Sort events chronologically
    all_events.sort(key=lambda x: (x["startTs"], x.get("summary", "")))
    if len(all_events) > MAX_EVENTS_TOTAL:
        print(
            f"fetch-events: total events ({len(all_events)}) exceeds MAX_EVENTS_TOTAL ({MAX_EVENTS_TOTAL}), truncating",
            file=sys.stderr,
        )
        all_events = all_events[:MAX_EVENTS_TOTAL]

    next_event = compute_next_event(all_events, now_ts, badge_minutes=args.badge_minutes)

    payload = {
        "updatedAt": now_ts,
        "events": all_events,
        "nextEvent": next_event,
    }

    payload_bytes = json.dumps(payload, indent=2).encode("utf-8")
    if len(payload_bytes) > MAX_OUTPUT_BYTES:
        for ev in all_events:
            ev["description"] = ""
        payload["events"] = all_events
        payload_bytes = json.dumps(payload, indent=2).encode("utf-8")

    if len(payload_bytes) > MAX_OUTPUT_BYTES:
        while all_events and len(payload_bytes) > MAX_OUTPUT_BYTES:
            all_events.pop()
            payload["events"] = all_events
            payload_bytes = json.dumps(payload, indent=2).encode("utf-8")

    if args.print:
        sys.stdout.buffer.write(payload_bytes)
        sys.stdout.buffer.write(b"\n")
        return 0

    abs_output = os.path.abspath(os.path.expanduser(args.output))
    out_dir = os.path.dirname(abs_output)
    out_name = os.path.basename(abs_output)

    try:
        write_private_file(out_dir, out_name, payload_bytes)
    except Exception as e:
        print(f"fetch-events: error saving cache to {args.output}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
