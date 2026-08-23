# AI_MEMORY

Running log of architectural decisions and their reasoning, kept up to date every phase so a
future AI session (or the project owner) doesn't accidentally reverse a deliberate choice. Modeled
on PropertyManager's `documentation/progress-log.md`, which the owner found valuable for session
continuity on a long, multi-week build.

Do not delete entries here just because a phase is "done" — this file's value is historical
context, not a current-status board (see `AI_HANDOFF.md` for that).

---

## 2026-08-23 — Project started, Phase 1 (Architecture) in progress

- Project named **InspectIQ** (inspection + AI/OCR angle). Repo created at
  `C:\Users\shmil\Projects\InspectIQ`, deliberately outside OneDrive (owner's explicit instruction
  — avoids OneDrive file-lock/sync issues with `node_modules`, `.venv`, and SQLite/log files that
  change frequently during dev).
- Full scope document (22 numbered prompts + 20-phase build order) preserved verbatim in
  `docs/SCOPE.md`. Individual prompts split into `prompts/*.md` for quick reference, but
  `SCOPE.md` is the canonical source — if anything conflicts, `SCOPE.md` wins.
- Git identity set to match the PropertyManager repo (`Stern-5565` / `shmillystern@gmail.com`) for
  consistency across the owner's projects.
- Following the same working style validated on PropertyManager: real-DB testing (no mocks), one
  module = one commit with an honest message, verify before claiming done, phase-gate at natural
  checkpoints for owner review rather than running the entire 20-phase build unattended.
