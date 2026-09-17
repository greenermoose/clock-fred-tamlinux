# AI Collaboration Session Archive: `fred.clock`

Chronological records of prompts, tool versions, and architectural decisions for `omarchy-fred-clock`.

---

## Session: 2026-09-11 — Clone Parity, `clonedFrom` & Countdown Badge (Milestone A)

- **Primary AI Agents**: Claude Code `2.1.267` (Planning) & Antigravity CLI `agy 1.2.2` (Implementation)
- **Primary Models**: Claude Opus 5 (`claude-opus-5`) & Gemini 3.8 Flash (High) (`gemini-3.8-flash-high`)
- **Commits**: `1a60de8`, `20442b8`
- **Transcript Reference**: Antigravity `0c27626f-8ff7-4c6e-a631-a281cf03b694`
- **Prompts**:
  > **Fred:**
  > "work on the fred.clock plugin. Ask if you have any questions."
  >
  > "How do I authenticate gh on this machine? I already have an SSH key installed. What more do I need to do?"
  >
  > "Let's wait on submitting this to the plugin marketplace until we have something more to show."
  >
  > "First, wasn't there a countdown that we were going to include so I could tell if I had stock omarchy.clock or fred.clock installed?"
  >
  > "Okay, let's go for milestone B now."
- **Key Decisions & Implementation Notes**:
  - Cloned upstream `omarchy.clock` and established the `fred.clock` repository structure.
  - Adopted `omarchy.clonedFrom` in `manifest.json`. Proved that `clonedFrom` replaces the stock widget in-place, preserves user settings, routes summon calls, and enables clean rollback without bar re-layout.
  - Added visual countdown badge showing time until next upcoming agenda item.

---

## Session: 2026-09-12 — Read-Only Agenda & stdlib iCal Engine (v1.0.0, v1.1.0)

- **Primary AI Agent**: Antigravity CLI (`agy 1.2.2`)
- **Primary Model**: Gemini 3.8 Flash (High) (`gemini-3.8-flash-high`)
- **Commits**: `efc0575`, `7a27e22`, `1e5e8dc`, `b16d974`, `d47a979`
- **Transcript Reference**: Antigravity `0c27626f-8ff7-4c6e-a631-a281cf03b694`
- **Prompts**:
  > **Fred:**
  > "I need to test the plugin first before we submit it to the marketplace. Do not submit yet."
  >
  > "Remove the sample events. I want the calendar to be clean and empty so I can try importing a real Google calendar."
  >
  > "Tell me how to find my secret token for my Google calendars."
  >
  > "My calendars.json file is private, right? This will not bleed into the public plugin GitHub repo?"
  >
  > "This is the secret address of a calendar I want to see in fred.clock: [private Google Calendar iCal URL]"
  >
  > "Save this config and fetch my events."
  >
  > "Are the instructions clear about how to add events from Google calendars? Will events get automatically picked up or do people need to run a command? ... Are you running those additional commands to speed things up?"
  >
  > "Yes on both. And update the version number."
  >
  > "Publish the plugin on the omarchy plugin marketplace."
  >
  > "Replace 'Replaces stock omarchy.clock' with 'fred.clock replaces the stock omarchy.clock'"
- **Key Decisions & Implementation Notes**:
  - Zero external pip dependencies: implemented pure Python standard library RFC 5545 recurrence (`RRULE`, `EXDATE`, `RDATE`) engine in `fetch-events.py` using `zoneinfo` and `datetime`.
  - Ensured calendar configuration and cached events are stored privately under `~/.config/fred.clock/` and strictly gitignored from public repository releases.
  - Added root `preview.png` and submitted initial listing to the Omarchy Plugin Marketplace.
  - Acknowledged Antigravity as contributor via commit trailers.

---

## Session: 2026-09-12 — Local Event CRUD & Reminders (v1.2.0)

- **Primary AI Agent**: Antigravity CLI (`agy 1.2.2`)
- **Primary Model**: Gemini 3.8 Flash (High) (`gemini-3.8-flash-high`)
- **Commits**: `da26270`
- **Transcript Reference**: Antigravity `0c27626f-8ff7-4c6e-a631-a281cf03b694`
- **Prompts**:
  > **Fred:**
  > "Now add the ability to create events in my local calendar. This will update the version of fred.clock."
- **Key Decisions & Implementation Notes**:
  - Added standalone local event creation, editing, and deletion helper `manage-event.py`.
  - Implemented atomic file writes for `events.json` cache updates.
  - Added desktop reminders via `notify-send` without requiring heavyweight background daemon dependencies.

---

## Session: 2026-09-13 — Marketplace Security Remediation (v1.3.0)

- **Primary AI Agent**: Antigravity CLI (`agy 1.2.2`)
- **Primary Model**: Gemini 3.8 Flash (High) (`gemini-3.8-flash-high`)
- **Marketplace Issue**: [omacom/omarchy-plugin-marketplace#6509](https://github.com/omacom/omarchy-plugin-marketplace/issues/6509)
- **Commits**: `28bb9b8`, `b84e380`, `f4fef2c`, `e62e552`, `40b2f53`, `a16e9e6`
- **Transcript Reference**: Antigravity `daa8b90d-550d-4b27-b6a0-f407a3fe7c6c`
- **Prompts**:
  > **Fred:**
  > "work on fred.clock version 1.3.0. Ask if you have questions."
  >
  > "I need to do some testing of the updated version of fred.clock before we claim that we have it working."
- **Key Decisions & Implementation Notes**:
  - Replaced ad-hoc `Process` instances with a single supervisor component `Launch.qml`.
  - Implemented closed environment (`clearEnvironment: true`, minimal `PATH`).
  - Added strict watchdog execution deadlines (5–10s) and bounded input sizes (max 5MB for iCal payloads, 500KB for calendar configs).
  - Implemented descriptor-relative temp creation (`O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`) and atomic rename via `dir_fd` to prevent symlink traversal or clobbering.
  - Authored comprehensive automated security test suite `tests/test_limits.py`.

---

## Session: 2026-09-15 — Post-Suspend Clock Freeze & Multi-Monitor Resync (v1.3.1)

- **Primary AI Agent**: Antigravity CLI (`agy 1.2.2` / `1.2.3`)
- **Primary Model**: Gemini 3.8 Flash (High) (`gemini-3.8-flash-high`)
- **Commits**: `de877c5`
- **Transcript Reference**: Antigravity `1e9ddb7c-ea23-4962-99fb-8f7df3252f94`
- **Prompts**:
  > **Fred:**
  > "Why did clock not update after a suspend? My left monitor page was showing the first time while my right monitor page was showing the correct time. My left monitor desktop spontaneously updated to the correct time after about a minute of showing the wrong time after resuming from suspend. Please investigate the cause and propose a fix."
  >
  > "Does this mean the plugin will be checking drift from wall clock every second all the time unless my system is suspended or hibernating?"
  >
  > "I prefer event driven. What signals is fred.clock already listening for?"
  >
  > "All things considered, do you think it's better to have the clock running a 1 second loop to check for drift against wall clock or to have an event-driven update after resuming from suspend? What's a better use of system resources?"
  >
  > "Let's fix the update on resume from suspend bug by implementing an event-driven solution. Create a plan and let me review it."
  >
  > "Proceed."
  >
  > "This was done with agy 1.2.2 with model Gemini 3.8 Flash. Is that recorded in the code and pushed to GitHub?"
- **Key Decisions & Implementation Notes**:
  - Diagnosed root cause from compositor and system logs: Quickshell's `SystemClock` (`src/core/clock.cpp`) uses a `QTimer` based on `CLOCK_MONOTONIC`, which stops advancing during S3 sleep. Upon waking, the timer had to finish counting down its remaining ~50 seconds before firing. The right monitor (`HDMI-A-1`) displayed the current time only because of a brief DRM hotplug disconnect/reconnect cycle that recreated its bar surface.
  - Chose pure event-driven architecture over a 1-second continuous QML watchdog timer to preserve CPU low-power C-states and avoid 86,400 unnecessary timer wakeups per day.
  - Enhanced `refresh()`: toggles `clock.enabled = false; clock.enabled = true;` to abort Quickshell's stale monotonic timer, read fresh wall time, and immediately clear expired event badges.
  - Added `broadcastClock("refresh")` across `bar._moduleWidgets` so IPC calls propagate across all connected displays (`DP-2` and `HDMI-A-1`).
  - Added `omarchy-shell -q omarchy.clock refresh &` to `msi-mp161-resume-workaround` triggered upon D-Bus `PrepareForSleep(false)` and `hypridle` `on-resume`.

---

## Session: 2026-09-16 — Launch.qml never compiled; closed env never applied (v1.3.2)

- **Primary AI Agent**: Claude Code (`claude 2.1.273`)
- **Primary Model**: Claude Opus 5 (`claude-opus-5`)
- **Commits**: _(see git log for v1.3.2)_
- **Transcript Reference**: Claude Code `8657ead7-7e1f-47a8-a5ab-2522fff58adb`
- **Prompts**:
  > **Fred:**
  > "My MSI is flickering again. I'm not sure when it started but it seems to be getting worse. Also, fred.clock is broken. What happened to my clock and calendar?! Please find and fix the root cause of both of these problems. I don't know if they are related."
- **Key Decisions & Implementation Notes**:
  - Shell journal: `Plugin widget fred.clock failed: BarWidget.qml:48:3: Type Launch unavailable — Launch.qml:36:3: Cannot assign to non-existent default property`. Reproduced standalone with `quickshell -p` and `QML_DISABLE_DISK_CACHE=1`: `Quickshell.Io.Process` has no default property, so `Timer` children are invalid QML. The component had never compiled since it was introduced in 1.3.0 (commit `28bb9b8`).
  - Why nobody noticed: Qt's qmlcache validates by source mtime only; Nix-store files carry mtime 1970, so the running bar kept serving the pre-1.3.0 compile of `BarWidget.qml` through every deploy and restart. The first `omarchy-qmlcache-purge` (added the same evening for fred.workspaces) exposed it. The 1.3.0 security remediation and 1.3.1 resume fix were therefore never actually running on the workstation.
  - Fix 1: watchdog timers become `readonly property Timer termTimer/killTimer` on the `Process` (object-valued properties instead of children); call sites unchanged.
  - Fix 2 (found while testing the first): `Model.pickEnv` checked `typeof Quickshell !== "undefined"` inside a `.js` library, where module singletons are never in scope, so every supervised process ran with `PATH` only. `pickEnv(keys, extra, lookup)` now takes a lookup function and `Launch.qml` passes `Quickshell.env`.
  - Unrelated to the MSI flicker: that is amdgpu KIQ TLB-flush failures after a hibernation resume (kernel bug 219492), recorded in `omarchy-config` docs.
- **Verification**:
  - Standalone harness: component loads; child sees exactly `HOME` + `PATH=/usr/bin`; a wedged `sleep 30` with `deadlineMs: 1500` exits with signal 15 after 1502 ms.
  - Live bar via `omarchy-fred-plugin dev fred.clock on` (cache purge + restart): no fred.clock warnings in the shell journal; `~/.cache/fred.clock/events.json` rewritten by the fetcher under the closed env; clock label visible on the center bar (screenshot).
  - `omarchy-notification-send`, `xdg-settings` and `wl-copy` each run under the exact allowlisted environment from a clean `env -i`.
  - `python3 -m unittest discover -s tests`: 21 tests OK.

