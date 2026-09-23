# GitHub repository rename — 2026-09-22

- **Tool**: Codex CLI `0.155.1`
- **Model**: `gpt-6-sol`
- **Transcript**: `01a0cbc5-55fc-7b33-bdea-230b6f8502ed`
- **Prompt**:
  > Please get up to speed on the plan to finish up in-progress omarchy plugin work, then rename my existing GitHub repos from omarchy-fred-* to *-fred-tamlinux. Check to see what plugins we've submitted to the marketplace that are midstream, had security reviews, and have not yet been resubmitted. I want to get those done with the security fixes required, and resubmit them so the review work is not done in vain.
- **Clarification**: Fred chose stem-only naming.
- **Change**: GitHub repository `omarchy-fred-clock` became `clock-fred-tamlinux`; local origin and current README, manifest, and other active repository links were updated. Local checkout paths remain unchanged.
- **Verification**: GitHub repository listing showed the new name; metadata changes were checked with `git diff --check`.
