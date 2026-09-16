# [Plugin] omarchy-fred-clock = a better clock and calendar showing events and countdown

Hello world!

I'm using omarchy as my daily driver and needed to show upcoming appointments and events from other calendars, especially from a variety of Google calendars for personal, family, and work events. So I had my AIs improve the stock Omarchy clock as a shell bar widget plugin: **`fred.clock`** ([Omarchy Plugin Marketplace](https://plugins.omarchy.org/plugin.html?id=fred.clock) • [GitHub Repo](https://github.com/greenermoose/omarchy-fred-clock)).

It replaces the default `omarchy.clock` widget in Omarchy's status bar, preserving all existing settings while adding upcoming event countdown badges directly on the bar, an interactive agenda for any selected day, and privacy-first multi-calendar synchronization.

[![Bar Countdown Badge](https://raw.githubusercontent.com/greenermoose/omarchy-fred-clock/main/assets/bar-countdown.png)](https://raw.githubusercontent.com/greenermoose/omarchy-fred-clock/main/assets/bar-countdown.png)

[![Clock with Countdown Badge and Calendar Agenda](https://raw.githubusercontent.com/greenermoose/omarchy-fred-clock/main/assets/screenshot.png)](https://raw.githubusercontent.com/greenermoose/omarchy-fred-clock/main/assets/screenshot.png)

### Problem Solved

The stock `omarchy.clock` widget is clean and functional for viewing the date/time and browsing a month grid, but it operates in a silo without awareness of your actual schedule. 

If you juggle multiple Google or iCalendar feeds (personal, work, family, side projects), you typically have to keep a browser tab open, run a bulky background calendar app, or check your phone just to see what meeting or appointment is next. 

`fred.clock` turns the shell bar clock into an active heads-up display:
1. **At-a-glance countdown**: You see what's coming up within the next hour directly in your bar without clicking anything.
2. **One-click schedule check**: Clicking the clock opens an interactive day agenda showing all your meetings, color-coded across all your feeds, with direct 1-click meeting join buttons.
3. **No OAuth complexity or daemons**: Subscribes directly to private iCal (`.ics`) URLs via Python standard library. No tokens to renew, zero write risk to your external calendars, and no background daemon footprint.

### Highlights & Features

- **Next-Event Countdown Badge**: When an event starts within 60 minutes (configurable via `badgeMinutes`), the bar widget displays the event title and remaining time directly beside the clock (e.g. `Fri Sep 11 16:28 • Team Sync in 17m` or `Team Sync now`).
- **Interactive Day Agenda**: Selecting any day in the month grid displays scheduled event cards with start/end times, account badges, and event locations.
- **1-Click Meeting Join**: Automatically detects Google Meet, Zoom, Microsoft Teams, and Webex meeting links and renders safe, direct `Join` buttons.
- **Multi-Calendar Sync**: Aggregates any number of remote `.ics` secret URLs (Google Calendar, Outlook, Fastmail, Apple iCloud) and local `.ics` files.
- **Account Filter Chips**: Filter the day's view on the fly using account chips (`All`, `Personal`, `Work`, `Projects`, etc.).
- **Local Event Management**: Add and delete private local events directly from the UI (`+` button or `n` key) or via CLI (`manage-event.py`), stored in standard RFC 5545 format at `~/.config/fred.clock/local.ics`.
- **Markdown Agenda Export**: Copy any day's full agenda as structured Markdown to your clipboard by pressing `y` or clicking the copy button.
- **Automatic Background Sync**: Pulls and caches events reactively when you edit `calendars.json`, periodically every 15 minutes, and whenever you open the panel (if the cache is >5m old).
- **In-Place Stock Replacement**: Uses Omarchy's `clonedFrom: "omarchy.clock"` routing so it seamlessly inherits all your custom date/time formats and cycle rings.
- **Least-Privilege Security Model**: Runs child processes exclusively through a supervised `Launch.qml` runner with closed environments, strict execution timeouts, and capped buffer limits.

### Installation

Install and enable with a single command via Omarchy's plugin manager:

```bash
omarchy plugin add https://github.com/greenermoose/omarchy-fred-clock.git --enable --yes
```

*(Or discover and install it directly via the [Omarchy Plugin Marketplace](https://plugins.omarchy.org/plugin.html?id=fred.clock).)*

#### Bar Center Anchor

Because Omarchy's bar center anchor is not automatically rewritten when enabling a clone, update `centerAnchor` in `~/.config/omarchy/shell.json`:

```bash
sed -i 's/"centerAnchor": "omarchy.clock"/"centerAnchor": "fred.clock"/' ~/.config/omarchy/shell.json
```

### Quick Setup: Adding Your Calendars

Add your calendar feeds in `~/.config/fred.clock/calendars.json` (permissions `0600`):

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
    "name": "Work Calendar",
    "url": "https://calendar.google.com/calendar/ical/your-work%40company.com/private-yyyy/basic.ics",
    "color": "#34a853",
    "enabled": true
  }
]
```

> **How to get your Google Calendar private URL**:
> In Google Calendar → Settings (⚙️) → select your calendar under "Settings for my calendars" → scroll down to "Integrate calendar" → copy the **"Secret address in iCal format"** URL (*not* the public one).

The plugin watches this file and triggers an automatic refresh the moment you save it.

### Interactions & Shortcuts

- **Left Click Bar**: Open or close the calendar & agenda popup.
- **Right Click Bar**: Cycle configured date and time formats.
- **Middle Click Bar**: Open Omarchy's timezone picker (`omarchy-menu-timezone`).
- **`n` / `a`** (or `+` button): Open inline form to create a new local event.
- **`y`** (or copy button): Copy the selected date's agenda as Markdown.
- **`t`**: Return view to today.
- **`[` / `]`**: Previous / next month.
- **`w`**: Toggle week start day (Sunday vs. Monday).
- **Escape**: Close the new event form or close the panel.

---

Check out the repository at:
--> https://github.com/greenermoose/omarchy-fred-clock

Omarchy Plugin Marketplace:
--> https://plugins.omarchy.org/plugin.html?id=fred.clock

Ask if you have any questions!
