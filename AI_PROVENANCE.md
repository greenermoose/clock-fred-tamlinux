# AI Collaboration & Provenance

This repository practices transparent AI-assisted engineering. We document the AI tools, models, prompts, and architectural decisions that shaped `fred.clock`.

---

## 1. Fred's Multi-Agent AI Toolchain

Rather than relying on a single AI model or interface, Fred uses a specialized toolchain tailored to each tool's strengths. CLI versions below were captured on 2026-09-13 (`<tool> --version`).

| Tool & Interface | CLI Version | Backing Models | Primary Role in the Ecosystem |
| :-- | :-- | :-- | :-- |
| **Claude Code** (`claude`) | `2.1.267` | Claude Opus 5 (`claude-opus-5`) | **Architecture & System Planning**: Authoring durable system specifications, multi-step runbooks, and cross-cutting policies. |
| **Codex CLI** (`codex`) | `0.154.0` | `gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra` | **Architecture & System Planning**: Second opinion on plans and specifications alongside Claude. |
| **Antigravity CLI** (`agy`) | `1.2.2` / `1.2.3` | Gemini 3.8 Flash (High) | **Coding, Refactoring & Implementation**: Primary coding partner for multi-file pair-programming, security remediation, bash/Python/QML engineering, and git release workflow. |
| **OpenCode** (`opencode`) | `1.18.30` | Big Pickle | **Distro & System Q&A**: Efficient lookups for Arch Linux / Omarchy package specifics and shell configuration, conserving frontier-model token budgets. |
| **Grok CLI** (`grok`) | `1.0.25` (`f7e67d6988e2`, stable) | Grok 4.6 | **Workstation Support**: Additional debugging, hardware diagnostics, and alternative implementation analysis. |

---

## 2. Key Architectural Milestones & AI Role

| Milestone | Version | Primary AI Partner | Key Decisions & Achievements |
| :-- | :-- | :-- | :-- |
| **Milestone A (Clone & Rebrand)** | `v0.1.0` | Claude & Antigravity | Cloned stock `omarchy.clock`, adopted `omarchy.clonedFrom` for in-place bar replacement, preserved stock settings, added countdown badge. |
| **Milestone B (Agenda & Sync)** | `v1.0.0` – `v1.1.0` | Antigravity (Gemini) | Pure Python stdlib recurrence engine (`fetch-events.py`), Google Calendar secret iCal feed sync, interactive agenda popout. |
| **Local Calendar CRUD** | `v1.2.0` | Antigravity (Gemini) | Local event creation, editing, deletion via `manage-event.py`, atomic JSON storage, `notify-send` desktop alerts. |
| **Security Remediation** | `v1.3.0` | Antigravity (Gemini) | Omarchy Plugin Marketplace review remediation (issue #6509): centralized `Launch.qml` runner, closed environment, strict timeouts, input size limits, file descriptor validation. |
| **Post-Suspend Resync & Multi-Monitor IPC** | `v1.3.1` | Antigravity (Gemini 3.8 Flash) | Resynchronize `SystemClock` and recalculate event countdown badge on wake from suspend by cycling `clock.enabled`. Relay IPC commands across displays via `bar._moduleWidgets`. |

Detailed session logs and prompts are documented in [`docs/ai/sessions.md`](docs/ai/sessions.md).
