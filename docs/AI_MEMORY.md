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

## 2026-08-23 — InspectionResponse snapshot strategy confirmed (PROJECT_PLAN.md §13.1)

Owner explicitly reviewed and confirmed the frozen-column snapshot approach over full
`InspectionTemplate` versioning, after asking specifically to be sure it wouldn't be regretted
later. Two mitigations were added as a direct result of that pushback, both **mandatory from
Phase 2, not optional**:

1. `InspectionQuestions`/Sections/Templates are soft-delete only — a hard delete would silently
   break the FK that the snapshot design deliberately keeps for analytics joins. Enforce at the
   repository layer (no `DELETE` statement against these tables), don't rely on convention alone.
2. `InspectionTemplate.Version` (bumped on any edit to it or its children) +
   `Inspections.TemplateVersionUsed` (captured at inspection-start). Not full version history —
   doesn't reconstruct what a past version looked like — but cheaply answers "which inspections
   predate/postdate this checklist change," which was the realistic gap in the frozen-column-only
   plan. If real template versioning is ever needed later, this column is exactly the backfill
   data a `TemplateVersions` table would need, so the migration path stays additive.

**Why this matters for future sessions**: if Phase 2's SQL ever ships without the soft-delete
enforcement or the `Version`/`TemplateVersionUsed` columns, that's a regression from an explicit,
reviewed decision — not a simplification to wave through in code review.
