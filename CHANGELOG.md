# Changelog

All notable changes to `fred.clock` (`omarchy-fred-clock`) will be documented in this file.

## [1.3.0] - 2026-09-13

### Security Remediation
Addressed marketplace security review on [omacom/omarchy-plugin-marketplace#6509](https://github.com/omacom/omarchy-plugin-marketplace/issues/6509):

- **Process Supervision & Sandboxing (F1)**:
  - Supervised all child process launches through `Launch.qml` with absolute executable paths (`/usr/bin/python3`, `/usr/bin/xdg-open`, `/usr/bin/wl-copy`, `$OMARCHY_PATH/bin/omarchy-notification-send`).
  - Helper scripts resolved sibling-relative to the loaded QML component via `Model.helperPath(Qt.resolvedUrl)`.
  - All processes execute with `clearEnvironment: true` and closed, strict environment variable allowlists.
  - QML watchdogs (SIGTERM on deadline, SIGKILL after 3s) backed by Python self-imposed `signal.alarm(45)` and `resource.setrlimit` (`RLIMIT_CPU`, `RLIMIT_AS`, `RLIMIT_FSIZE`, `RLIMIT_NOFILE`).

- **Input Caps & Bounded Expansion (F2)**:
  - Enforced strict upper bounds: `MAX_CONFIG_BYTES` (64 KiB), `MAX_FEEDS` (32), `MAX_FEED_BYTES` (8 MiB), `FEED_DEADLINE_S` (20s), `MAX_LINE_BYTES` (64 KiB), `MAX_LINES` (200,000), `MAX_VEVENTS_PER_FEED` (20,000), `MAX_EXDATES` (2,000), `MAX_INSTANCES_PER_EVENT` (1,000), `MAX_SUMMARY` (512), `MAX_LOCATION` (2,048), `MAX_DESCRIPTION` (4,096), `MAX_EVENTS_TOTAL` (5,000), `MAX_OUTPUT_BYTES` (4 MiB).
  - Streamed chunked reads (64 KiB) for remote and local feeds with monotonic wall-clock deadlines.
  - Generator-based line unfolding in `unfold_ics`.
  - Strict HTTPS-only redirect handler (`_HttpsOnlyRedirect`) capping redirect hops at 5.
  - Bounded recurrence engine: clamped `INTERVAL` [1, 366] and `COUNT` [1, 10,000], guarded every recurrence loop against `MAX_INSTANCES_PER_EVENT`.
  - Guaranteed bounded JSON cache output: sheds descriptions first and truncates events before writing, never writing a partial document.

- **Descriptor-Relative Atomic Cache Writes (F3)**:
  - Replaced path-based `tempfile.mkstemp` and `os.replace` with `write_private_file`.
  - Target directory validation: verified self-owned directory (`getuid()`), private mode `0700`, parent directory non-world-writable unless sticky.
  - Descriptor-relative temp creation (`O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`) and atomic rename via `dir_fd`; prevents symlink traversal or clobbering.

- **Shell & Detached Execution Elimination (F4)**:
  - Completely eliminated `Quickshell.execDetached` and shell invocations (`bash -c`).
  - Clipboard copy writes agenda Markdown directly to `/usr/bin/wl-copy` stdin.
  - Meeting URL regex validated and capped at 2,048 characters before passing to `/usr/bin/xdg-open`.
  - Local event management uses shared `manageProc` in `BarWidget`, preventing concurrent modification collisions.
  - Dropped redundant nested `trigger_fetch` and `subprocess` import from `manage-event.py`.

## [1.2.0] - 2026-09-13

### Added
- Local calendar event management with persistent RFC 5545 storage at `~/.config/fred.clock/local.ics`.
- Interactive modal UI for creating and deleting events.
- Omarchy Shell IPC commands (`createEvent`, `deleteEvent`).
- CLI tool `manage-event.py` for headless local event management.

## [1.1.0] - 2026-09-12

### Added
- Automatic cache invalidation and re-fetch when `calendars.json` is modified.
- Comprehensive Google Calendar secret URL configuration guide.
- Antigravity pair-programming acknowledgments.

## [1.0.0] - 2026-09-12

### Added
- Interactive agenda panel for the selected date beneath the month grid.
- Multi-calendar feed synchronization (remote secret `.ics` URLs and local files).
- Next-event countdown badge on the bar widget.
- Meeting URL automatic detection and 1-click join.
- Multi-account filter chips.
- Keyboard shortcut `y` to copy the selected day's agenda as structured Markdown.
- Root preview image for marketplace card display.

## [0.1.0] - 2026-09-11

### Added
- Initial release cloned from stock `omarchy.clock`.
- In-place replacement via `omarchy.clonedFrom` manifest mapping.
- Prototype next-event countdown badge.
