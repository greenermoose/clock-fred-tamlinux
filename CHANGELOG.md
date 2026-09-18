# Changelog

All notable changes to `fred.clock` (`omarchy-fred-clock`) will be documented in this file.

## [1.3.3] - 2026-09-18

### Added
- **Version Footers**: Embedded running version in bar hover tooltip (`BarWidget.qml`) and as a centered, styled footer at the bottom of the open agenda popup panel (`Panel.qml`).
- Bumped `USER_AGENT` in `fetch-events.py` to `1.3.3`.

## [1.3.2] - 2026-09-16

### Fixed
- **`Launch.qml` never compiled** (widget vanished from the bar, replaced by the shell's fallback icons): `Quickshell.Io.Process` has no default property, so the two watchdog `Timer` children made the component fail with `Cannot assign to non-existent default property` and every `Launch { }` call site with `Type Launch unavailable`. The timers are now object-valued properties (`termTimer`, `killTimer`) of the `Process`.
- **Closed environment allowlist was never applied**: `Model.pickEnv` probed for the `Quickshell` singleton from a plain JavaScript library, where QML module singletons are not in scope, so every supervised process received only `PATH`. `Launch.qml` now passes `Quickshell.env` in as a lookup function; the fetcher gets `HOME`/`TZ`/`LANG`/`XDG_*` again and the notifier its Wayland/D-Bus variables.
- `USER_AGENT` in `fetch-events.py` now carries the real version.

### Why 1.3.0 and 1.3.1 appeared to work
Qt validates its on-disk QML cache (`~/.cache/quickshell/qmlcache`) by source mtime only, and Home Manager deploys the plugin from the Nix store where every file has mtime 1970. The bar kept serving the pre-1.3.0 compile of `BarWidget.qml` (no `Launch` reference) across every deploy and shell restart; the first cache purge (2026-09-16) exposed the failure. Deploys must purge the cache (`omarchy-qmlcache-purge`) before restarting the shell — see `omarchy-fred-plugin dev|update`.

## [1.3.1] - 2026-09-15

### Fixed
- **Post-Suspend Clock Freeze & Multi-Monitor Resync**:
  - Toggled `clock.enabled = false; clock.enabled = true;` inside `refresh()` to abort Quickshell's stale monotonic `QTimer` (`src/core/clock.cpp`), force an immediate wall-clock query, and reschedule the timer to the next upcoming minute mark.
  - Implemented `broadcastClock("refresh")` across `bar.moduleWidgets || bar._moduleWidgets` so that `omarchy-shell omarchy.clock refresh` and `fred.clock` IPC calls update clock widgets across all active monitors simultaneously.
  - Recalculated agenda countdown badges immediately upon wake (`recalculateBadge()`) so stale countdowns (e.g. past events) disappear without waiting for network calendar fetch loops.
  - Added dedicated `fred.clock` `IpcHandler` alongside stock `omarchy.clock`.

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
