# Session: 2026-09-16 — Launch.qml Never Compiled; Closed Env Never Applied (v1.3.2)

- **Primary AI Agent**: Claude Code (`claude`)
- **Primary Model**: Claude Opus 5 (`claude-opus-5`) — confirmed from `"model"` field in transcript
- **Claude version**: `2.1.273` — confirmed from `"version"` field in transcript
- **Transcript**: Claude Code `8657ead7-7e1f-47a8-a5ab-2522fff58adb`
- **Session start**: 2026-09-16T22:39:51-04:00 (from transcript timestamp `2026-09-17T02:39:51.316Z` UTC)
  — **Note**: the prior `sessions.md` date of `2026-09-16` is correct (local time).
- **Commits**: `5b6f3f1` (2026-09-16 22:52)

## Prompts (verbatim from transcript)

> **Fred:** "My MSI is flickering again. I'm not sure when it started but it seems to be getting worse. Also, fred.clock is broken. [screenshot attached] What happened to my clock and calendar?! Please find and fix the root cause of both of these problems. I don't know if they are related."

## Key Decisions & Implementation Notes

- Shell journal: `Plugin widget fred.clock failed: BarWidget.qml:48:3: Type Launch unavailable
  — Launch.qml:36:3: Cannot assign to non-existent default property`. Reproduced standalone
  with `quickshell -p` and `QML_DISABLE_DISK_CACHE=1`: `Quickshell.Io.Process` has no
  default property, so `Timer` children are invalid QML. The component had never compiled
  since it was introduced in 1.3.0 (commit `28bb9b8`).
- Why nobody noticed: Qt's qmlcache validates by source mtime only; Nix-store files carry
  mtime 1970, so the running bar kept serving the pre-1.3.0 compile of `BarWidget.qml`
  through every deploy and restart. The first `omarchy-qmlcache-purge` (added the same
  evening for fred.workspaces) exposed it. The 1.3.0 security remediation and 1.3.1 resume
  fix were therefore never actually running on the workstation.
- Fix 1: watchdog timers become `readonly property Timer termTimer/killTimer` on the
  `Process` (object-valued properties instead of children); call sites unchanged.
- Fix 2 (found while testing the first): `Model.pickEnv` checked
  `typeof Quickshell !== "undefined"` inside a `.js` library, where module singletons are
  never in scope, so every supervised process ran with `PATH` only. `pickEnv(keys, extra,
  lookup)` now takes a lookup function and `Launch.qml` passes `Quickshell.env`.
- Unrelated to the MSI flicker: that is amdgpu KIQ TLB-flush failures after a hibernation
  resume (kernel bug 219492), recorded in `omarchy-config` docs.

## Verification (from transcript)

- Standalone harness: component loads; child sees exactly `HOME` + `PATH=/usr/bin`;
  a wedged `sleep 30` with `deadlineMs: 1500` exits with signal 15 after 1502 ms.
- Live bar via `omarchy-fred-plugin dev fred.clock on` (cache purge + restart): no
  fred.clock warnings in the shell journal; `~/.cache/fred.clock/events.json` rewritten
  by the fetcher under the closed env; clock label visible on the center bar (screenshot).
- `omarchy-notification-send`, `xdg-settings` and `wl-copy` each run under the exact
  allowlisted environment from a clean `env -i`.
- `python3 -m unittest discover -s tests`: 21 tests OK.
