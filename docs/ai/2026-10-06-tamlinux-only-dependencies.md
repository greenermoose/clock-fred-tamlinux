# Tamlinux-only dependencies for 2.0.0

- **Date**: 2026-10-06
- **CLI Tool**: Claude Code (`claude`) `2.1.291`, from `detect-runtime.sh`.
- **Model**: Claude Opus 5.5 (`claude-opus-5-5`)
- **Authorship**: Fred asked for the next step after Tamlinux 0.2.6 and approved the plan. Claude made the change on `develop/2.0.0`. Fred chose how plugins find Tamlinux commands.
- **Commit**: This commit.
- **Transcript**: Retained privately by the author.

## Guiding prompts

> I had to recover from a KIQ error. That interrupted opencode as it was working on T15. I believe you're done with 0.2.6 of the tamlinux project. What's next for you? Anything for agy to work on? opencode is very slow this morning, but I've prompted it to "Read AGENTS.md and your inbox. Check to see how far you got. Continue from where you left off." We'll see what it does. So far it has only read AGENTS.md after several minutes.

> Go ahead

Fred's answer to the question of how plugins should find Tamlinux's commands:

> TAMLINUX_BIN variable (Recommended)

## Work and decisions

Notifications run `tam-notification-send` by absolute path from `TAMLINUX_BIN`, falling back to `~/.local/bin`. `OMARCHY_PATH` is no longer read or copied into the closed environment.

`tests/test_no_omarchy.py` is new: it fails on any `omarchy-*` command or layer name, `/usr/share/omarchy` path, or `OMARCHY_*` variable in a shipped file outside comments, and checks that each allowance is still used.

Plugins find Tamlinux's own commands as `TAMLINUX_BIN + "/tam-..."`, never by bare name; the session sets `TAMLINUX_BIN` to `~/.local/bin` today. Not tagged or released.

## Verification

- Boundary test passes, and fails on the previous tree. Existing suite: 1 failure, `test_oversized_remote_feed`, which fails the same way on the previous tree.
