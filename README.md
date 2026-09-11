# Clock with Countdown Badge (`fred.clock`)

An opinionated Omarchy shell bar widget and calendar panel featuring upcoming event countdowns, multi-calendar support, and seamless in-place replacement of the stock Omarchy clock.

![Clock with Countdown Badge](assets/screenshot.png)

---

## Overview

`fred.clock` replaces the default `omarchy.clock` widget in Omarchy's status bar, preserving all existing settings while adding upcoming event countdown badges directly to the bar:

| Feature | Description |
| :--- | :--- |
| **In-Place Replacement** | Replaces `omarchy.clock` in-place using Omarchy's `clonedFrom` routing. Stock date/time formats and cycle rings carry over automatically. |
| **Countdown Badge** | Displays upcoming events starting within 60 minutes directly on the bar (`HH:mm • Team Sync in 12m` or `Team Sync now`). |
| **Multi-Calendar Sync** | Fetches read-only schedules from Google Calendar or any iCalendar (`.ics`) secret URLs and local files with zero external dependencies. |
| **Interactive Calendar** | Full calendar popup with month grid, week-start toggle, ISO week numbers, and timezone switcher. |

---

## Features

- **Next-Event Countdown**: When an event is within 60 minutes (configurable via `badgeMinutes`), the bar widget displays the event title and time remaining.
- **Privacy-First & Read-Only**: Consumes private `.ics` subscription URLs via standard HTTP GET. No OAuth tokens, no write permissions, no risk of accidental modifications or unwanted invite dispatches.
- **Zero Daemon Dependencies**: Uses Python 3 standard library only (`ThreadPoolExecutor`, `urllib`, `zoneinfo`) for background fetching without extra background daemons.
- **Robust Recurrence**: Supports standard RFC 5545 recurrence rules (`RRULE`), exclusions (`EXDATE`), and timezone normalization.
- **Non-Blocking Quickshell Integration**: Events are cached atomically at `~/.cache/fred.clock/events.json` (mode 0600) and watched reactively by Quickshell.

---

## Installation

Install using Omarchy's plugin manager:

```bash
omarchy plugin add https://github.com/greenermoose/omarchy-fred-clock.git --enable --yes
```

### Bar Center Anchor

Because Omarchy's bar center anchor is not automatically rewritten by plugin enabling, set `centerAnchor` in `~/.config/omarchy/shell.json`:

```bash
sed -i 's/"centerAnchor": "omarchy.clock"/"centerAnchor": "fred.clock"/' ~/.config/omarchy/shell.json
```

---

## Configuration

### Calendar Feeds

Configure your calendars in `~/.config/fred.clock/calendars.json` (permissions `0600`):

```json
[
  {
    "account": "Personal",
    "name": "Personal Calendar",
    "url": "https://calendar.google.com/calendar/ical/your-address%40gmail.com/private-xxxx/basic.ics",
    "color": "#4285f4",
    "enabled": true
  },
  {
    "account": "Work",
    "name": "Team Calendar",
    "url": "https://calendar.google.com/calendar/ical/your-org%40group.calendar.google.com/private-yyyy/basic.ics",
    "color": "#34a853",
    "enabled": true
  },
  {
    "account": "Local",
    "name": "Local Events",
    "path": "~/Documents/calendar.ics",
    "color": "#fbbc05",
    "enabled": false
  }
]
```

### Bar Settings

Inline widget settings in `~/.config/omarchy/shell.json`:

- `format`: Clock date/time format string (default: `"ddd MMM d HH:mm"`).
- `formatAlt`: Alternative date/time format string (default: `"d MMMM 'W'ww yyyy"`).
- `verticalFormat`: Format string when the bar is vertical (default: `"HH\n—\nmm"`).
- `badgeMinutes`: Maximum minutes ahead to show upcoming event countdown badges (default: `60`, set to `0` to disable).

---

## Interactions & Shortcuts

- **Left Click**: Open / close the calendar panel.
- **Right Click**: Cycle through common date and time formats.
- **Middle Click**: Open the Omarchy timezone selector (`omarchy-menu-timezone`).

---

## Uninstallation

To remove `fred.clock` and restore the default stock clock:

```bash
sed -i 's/"centerAnchor": "fred.clock"/"centerAnchor": "omarchy.clock"/' ~/.config/omarchy/shell.json
omarchy plugin remove fred.clock
```

---

## License

GNU General Public License v3.0 or later. See [LICENSE](LICENSE) for details.
Upstream Omarchy MIT copyright and diff recipe documented in [UPSTREAM.md](UPSTREAM.md).
