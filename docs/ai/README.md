# AI Collaboration Session Archive: `omarchy-fred-clock`

Individual session records documenting prompt history, tools, models, and key
architectural decisions for `omarchy-fred-clock`.

> [!NOTE]
> All entries were verified against local transcript stores during migration on
> 2026-09-20. Where the agy CLI version could not be confirmed from transcript
> content, this is noted in the individual session file. See
> [`docs/agent-guides/ai-session-stores.md`](../../docs/agent-guides/ai-session-stores.md)
> for the store inventory and verification methodology.

## Session Records

| Date | Topic | Primary Tool | Model | Session Document |
| :-- | :-- | :-- | :-- | :-- |
| 2026-09-11 | Clone Parity, `clonedFrom` & Countdown Badge (v0.1.0) | `agy` | Gemini 3.8 Flash (High) | [`2026-09-11-clone-parity-clonedfrom-countdown-badge.md`](2026-09-11-clone-parity-clonedfrom-countdown-badge.md) |
| 2026-09-12 | Read-Only Agenda & stdlib iCal Engine (v1.0.0, v1.1.0) | `agy` | Gemini 3.8 Flash (High) | [`2026-09-12-read-only-agenda-ical-engine-v1.0.0.md`](2026-09-12-read-only-agenda-ical-engine-v1.0.0.md) |
| 2026-09-12 | Local Event CRUD & Reminders (v1.2.0) | `agy` | Gemini 3.8 Flash (High) | [`2026-09-12-local-event-crud-reminders-v1.2.0.md`](2026-09-12-local-event-crud-reminders-v1.2.0.md) |
| 2026-09-13 | Marketplace Security Remediation (v1.3.0) | `agy` | Gemini 3.8 Flash (High) | [`2026-09-13-marketplace-security-remediation-v1.3.0.md`](2026-09-13-marketplace-security-remediation-v1.3.0.md) |
| 2026-09-14 | Post-Suspend Clock Freeze & Multi-Monitor Resync (v1.3.1) | `agy` | Gemini 3.8 Flash (High) | [`2026-09-14-post-suspend-clock-freeze-v1.3.1.md`](2026-09-14-post-suspend-clock-freeze-v1.3.1.md) |
| 2026-09-16 | Launch.qml Never Compiled; Closed Env Never Applied (v1.3.2) | `claude` (Claude Code `2.1.273`) | Claude Opus 5 (`claude-opus-5`) | [`2026-09-16-launch-qml-never-compiled-v1.3.2.md`](2026-09-16-launch-qml-never-compiled-v1.3.2.md) |
| 2026-09-18 | Version Footers & Running Status Display (v1.3.3) | `agy` | Gemini 3.8 Flash (High) | [`2026-09-18-version-footers-running-status-v1.3.3.md`](2026-09-18-version-footers-running-status-v1.3.3.md) |

## Corrections vs. prior `sessions.md`

The following errors were found and corrected during transcript verification on 2026-09-20:

| Session | Error | Correction |
| :-- | :-- | :-- |
| Sep 13 (v1.3.0) | Dated `2026-09-14` | Transcript start: `2026-09-13T07:51:31-04:00` |
| Sep 14 (v1.3.1) | Dated `2026-09-15` | Transcript start: `2026-09-14T17:35:28-04:00` |
| Sep 14 (v1.3.1) | Missing prompt: "What if we wanted fred.clock to be able to show seconds ticking by?" | Added from transcript |
| Sep 16 (v1.3.2) | Prompt shown without screenshot notation | Transcript shows screenshot was attached |
| Sep 18 (v1.3.3) | 3 follow-up prompts omitted | Added from transcript |
| Sep 11–12 (v0.1.0–v1.2.0) | agy version given as `1.2.2` | Not confirmed in transcripts; noted as unverified |
| Sep 18 (v1.3.3) | agy version given as `1.2.6` | Not confirmable from transcript; noted as unverified |
