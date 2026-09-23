# Session: 2026-09-23 — Upstream survey foundation

- **CLI tool:** Codex CLI `0.156.1` (checked on 2026-09-23)
- **Model:** `gpt-6-sol` (verified in the Codex session transcript)
- **Content commit:** `ab645c7`
- **Transcript reference:** Codex session `01a0cf84-a164-7192-aa45-e04a7e64ca48`
- **Scope:** Documentation and survey structure for the clock repository; no field survey or product implementation.

## User direction

These are verbatim excerpts from Fred's prompts and replies relevant to public
work. The full transcript contains a private planning reference and remains
in the local session store.

> Tamlinux derives from omarchy and many other sources of inspiration. We should be keeping an UPSTREAM.md doc and an upstream folder for each repo to keep track of our sources of inspiration but also bug fixes, security improvements, and feature enhancements.

> When I say "survey the field for X" that should trigger a skill or runbook that goes out and does a good search, starting with the known references in our UPSTREAM.md file, but also looking for interesting forks or completely new projects that we can use to improve our own version of an application and the building blocks of our system.

> I will be asking agents to survey the field on a regular basis. I want the surveying done on my instigation to control token spend and direct the effort.

Fred clarified the scope as "Yes, all repos" and the decision boundary as
"Research and recommend first." He then directed: "commit and publish".

## Changes and verification

- Added or extended the root `UPSTREAM.md` with known starting references and
  a place to link future dated surveys. Existing clone provenance was preserved
  where present.
- Added `upstream/README.md` so the research directory is tracked in Git.
- Reviewed the staged file list and passed `git diff --cached --check`.
- No runtime code changed; no tests or field survey were run.
