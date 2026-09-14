# AI Collaboration & Provenance

This repository practices transparent AI-assisted engineering. We document the AI tools, models, prompts, and architectural decisions that shaped `fred.clock`.

---

## 1. Fred's Multi-Agent AI Toolchain

| Tool & Interface | Backing Models | Primary Role |
| :-- | :-- | :-- |
| **Claude Code & Codex** | Claude 3.7 Sonnet, o3-mini | Planning, system architecture, marketplace remediation plan authoring (`fred-clock-plan.md`, `fred-clock-security-remediation.md`). |
| **Antigravity CLI (`agy`)** | Gemini 3.8 Flash (High), Gemini 2.5 Pro | Implementation partner: countdown badge QML, multi-feed iCalendar recurrence engine in Python stdlib, local calendar event CRUD, marketplace security remediation (`Launch.qml`, rlimits, input caps, descriptor writes). |
| **OpenCode** | Open-source models | Omarchy shell QML and Quickshell process execution guidance. |

---

## 2. Key Architectural Milestones & AI Role

| Milestone | Version | Primary AI Partner | Key Decisions & Achievements |
| :-- | :-- | :-- | :-- |
| **Milestone A (Clone & Rebrand)** | `v0.1.0` | Claude & Antigravity | Cloned stock `omarchy.clock`, adopted `omarchy.clonedFrom` for in-place bar replacement, preserved stock settings, added countdown badge. |
| **Milestone B (Agenda & Sync)** | `v1.0.0` – `v1.1.0` | Antigravity (Gemini) | Pure Python stdlib recurrence engine (`fetch-events.py`), Google Calendar secret iCal feed sync, interactive agenda popout. |
| **Local Calendar CRUD** | `v1.2.0` | Antigravity (Gemini) | Local event creation, editing, deletion via `manage-event.py`, atomic JSON storage, `notify-send` desktop alerts. |
| **Security Remediation** | `v1.3.0` | Antigravity (Gemini) | Omarchy Plugin Marketplace review remediation (issue #6509): centralized `Launch.qml` runner, closed environment, strict timeouts, input size limits, file descriptor validation. |

Detailed session logs and prompts are documented in [`docs/ai/sessions.md`](docs/ai/sessions.md).
