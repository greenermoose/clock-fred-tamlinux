# Session: 2026-09-28 — Keep session IDs out of public provenance

- **CLI tool:** Claude Code `2.1.283` (as logged in the session transcript)
- **Model:** Claude Opus 5.5 (`claude-opus-5-5`, read from the session transcript)
- **Transcript**: Retained privately by the author.
- **Scope:** AI provenance documentation only; no runtime code changed.

## User direction

Fred's guiding prompts, verbatim, with private repository names redacted:

> I don't see the need to include the complete session id in public repos in the AI session docs. That seems like an unnecessary privacy risk. Please ponder and propose a solution to this. Why are we including the transcript reference and exact session ID? How does that help anyone who does not have access to my computer or account at that AI provider?

> Go with the private ledger and make the changes. Update the appropriate AI guides, sklls, runbooks, and memories on this system so all AI agents know how AI sessions should work and why. Both [redacted: private repository] and [redacted: private repository] are private repos. The others in the the tamlinux folder are public repos. I want to provide guidance to the public so that people can see how I use AI and determine the provenance of the code in each of our public repos, without divulging unnecessary private details.

Fred reviewed and edited the public standard, then directed: "Now commit each
repo with an appropriate message."

## Changes and verification

- Removed session, conversation, and rollout IDs (full and shortened) and
  local transcript paths from this repository's AI provenance records. Each
  record now says `Transcript: Retained privately by the author`, or states
  that its transcript was not verified. The IDs were first copied to Fred's
  private index, so no reference was lost.
- Added a "How to read this record" section to `AI_PROVENANCE.md` that links
  the Tamlinux [AI provenance standard](https://github.com/greenermoose/tamlinux/blob/main/docs/ai-provenance-standard.md).
- Searched the provenance files for full IDs and session-store paths, and read
  the diff for shortened IDs.
- Git history was not rewritten; earlier commits still contain the old IDs.
