# AI Collaboration Session Archive: `fred.clock`

Chronological records of prompts, tool versions, and architectural decisions for `omarchy-fred-clock`.

---

## Session: 2026-09-11 — Clone Parity, `clonedFrom` & Countdown Badge (Milestone A)
- **Primary AI Agent**: Claude Code `2.1.267` (Planning) & Antigravity CLI `agy 1.2.2` (Implementation)
- **Primary Model**: Claude Opus 5 & Gemini 3.8 Flash (High)
- **Key Decision**: Adopt `omarchy.clonedFrom` rather than manual swap. Proven that `clonedFrom` replaces the stock widget in-place, preserves settings, routes summon calls, and enables clean rollback.

---

## Session: 2026-09-12 — Read-Only Agenda & stdlib iCal Engine (v1.0.0, v1.1.0)
- **Primary AI Agent**: Antigravity CLI (`agy 1.2.2`)
- **Primary Model**: Gemini 3.8 Flash (High)
- **Key Decision**: Zero pip dependencies. Implement RFC 5545 recurrence (`RRULE`, `EXDATE`, `RDATE`) purely using Python standard library and `zoneinfo`. Atomic cache writes to prevent UI thread blocking.

---

## Session: 2026-09-12 — Local Event CRUD & Reminders (v1.2.0)
- **Primary AI Agent**: Antigravity CLI (`agy 1.2.2`)
- **Primary Model**: Gemini 3.8 Flash (High)
- **Key Decision**: Added local event creation and editing via `manage-event.py`. Implemented desktop notifications without requiring external daemon dependencies.

---

## Session: 2026-09-13 — Marketplace Security Remediation (v1.3.0)
- **Primary AI Agent**: Antigravity CLI (`agy 1.2.2`)
- **Primary Model**: Gemini 3.8 Flash (High)
- **Marketplace Issue**: [omacom/omarchy-plugin-marketplace#6509](https://github.com/omacom/omarchy-plugin-marketplace/issues/6509)
- **Key Decisions**:
  - Replaced ad-hoc `Process` instances with a single supervisor component `Launch.qml`.
  - Implemented closed environment (`clearEnvironment: true`, minimal `PATH`).
  - Added strict watchdog execution deadlines (5–10s).
  - Bounded input sizes (max 5MB for iCal payloads, 500KB for calendar configs).
  - Descriptor-relative temp creation (`O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`) and atomic rename via `dir_fd`; prevents symlink traversal or clobbering.
  - Added comprehensive automated security test suite `tests/test_limits.py`.

---

## Session: 2026-09-15 — Post-Suspend Clock Freeze & Multi-Monitor Resync (v1.3.1)
- **Primary AI Agent**: Antigravity CLI (`agy 1.2.2`)
- **Primary Model**: Gemini 3.8 Flash (High)
- **Prompts**:
  > "Why did clock not update after a suspend? My left monitor page was showing the first time while my right monitor page was showing the correct time. My left monitor desktop spontaneously updated to the correct time after about a minute of showing the wrong time after resuming from suspend. Please investigate the cause and propose a fix."
  > "Does this mean the plugin will be checking drift from wall clock every second all the time unless my system is suspended or hibernating?"
  > "I prefer event driven. What signals is fred.clock already listening for?"
  > "All things considered, do you think it's better to have the clock running a 1 second loop to check for drift against wall clock or to have an event-driven update after resuming from suspend? What's a better use of system resources?"
  > "Let's fix the update on resume from suspend bug by implementing an event-driven solution. Create a plan and let me review it."
  > "Proceed."
  > "This was done with agy 1.2.2 with model Gemini 3.8 Flash. Is that recorded in the code and pushed to GitHub?"
- **Key Decisions**:
  - Diagnosed root cause from compositor and system logs: Quickshell's `SystemClock` (`src/core/clock.cpp`) uses a `QTimer` based on `CLOCK_MONOTONIC`, which stops advancing during S3 sleep. Upon waking, the timer had to finish counting down its remaining ~50 seconds before firing. The right monitor (`HDMI-A-1`) displayed the current time only because of a brief DRM hotplug disconnect/reconnect cycle that recreated its bar surface.
  - Chose pure event-driven architecture over a 1-second continuous QML watchdog timer to preserve CPU low-power C-states and avoid 86,400 unnecessary timer wakeups per day.
  - Enhanced `refresh()`: toggles `clock.enabled = false; clock.enabled = true;` to abort Quickshell's stale monotonic timer, read fresh wall time, and immediately clear expired event badges.
  - Added `broadcastClock("refresh")` across `bar._moduleWidgets` so IPC calls propagate across all connected displays (`DP-2` and `HDMI-A-1`).
  - Added `omarchy-shell -q omarchy.clock refresh &` to `msi-mp161-resume-workaround` triggered upon D-Bus `PrepareForSleep(false)` and `hypridle` `on-resume`.
