# AI Collaboration Session Archive: `fred.clock`

Chronological records of prompts, tool versions, and architectural decisions for `omarchy-fred-clock`.

---

## Session: 2026-09-11 — Clone Parity, `clonedFrom` & Countdown Badge (Milestone A)
- **Primary AI Agent**: Claude Code (Planning) & Antigravity (Implementation)
- **Primary Model**: Claude 3.7 Sonnet & Gemini 2.5 Pro
- **Key Decision**: Adopt `omarchy.clonedFrom` rather than manual swap. Proven that `clonedFrom` replaces the stock widget in-place, preserves settings, routes summon calls, and enables clean rollback.

---

## Session: 2026-09-12 — Read-Only Agenda & stdlib iCal Engine (v1.0.0, v1.1.0)
- **Primary AI Agent**: Antigravity (`agy`)
- **Primary Model**: Gemini 3.8 Flash (High)
- **Key Decision**: Zero pip dependencies. Implement RFC 5545 recurrence (`RRULE`, `EXDATE`, `RDATE`) purely using Python standard library and `zoneinfo`. Atomic cache writes to prevent UI thread blocking.

---

## Session: 2026-09-12 — Local Event CRUD & Reminders (v1.2.0)
- **Primary AI Agent**: Antigravity (`agy`)
- **Primary Model**: Gemini 3.8 Flash (High)
- **Key Decision**: Added local event creation and editing via `manage-event.py`. Implemented desktop notifications without requiring external daemon dependencies.

---

## Session: 2026-09-13 — Marketplace Security Remediation (v1.3.0)
- **Primary AI Agent**: Antigravity (`agy`)
- **Primary Model**: Gemini 3.8 Flash (High)
- **Marketplace Issue**: [omacom/omarchy-plugin-marketplace#6509](https://github.com/omacom/omarchy-plugin-marketplace/issues/6509)
- **Key Decisions**:
  - Replaced ad-hoc `Process` instances with a single supervisor component `Launch.qml`.
  - Implemented closed environment (`clearEnvironment: true`, minimal `PATH`).
  - Added strict watchdog execution deadlines (5–10s).
  - Bounded input sizes (max 5MB for iCal payloads, 500KB for calendar configs).
  - Replaced direct path cache writes with descriptor-relative validation.
  - Added comprehensive automated security test suite `tests/test_limits.py`.
