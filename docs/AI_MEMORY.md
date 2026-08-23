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

## 2026-08-23 — Phase 2 SQL written and verified against a real local SQL Server

All 25 tables, every deferred `CHECK` constraint, and 43 indexes now exist in a real local
`InspectIQDb` (`localhost\SQLEXPRESS`, Windows auth via `sqlcmd`) — not just designed on paper.
Verified with actual test inserts (valid/invalid data, FK violations, duplicate-unique
violations), not just "the script ran without error."

**The soft-delete-only requirement from the §13.1 sign-off is enforced by three
`INSTEAD OF DELETE` triggers**, not just a repository-layer convention as originally scoped —
upgraded during implementation to match the same "structural guarantee, not app convention"
principle already used for `RiskAssessments.RiskScore` (a `PERSISTED` computed column). Verified
live: a hard `DELETE` against `InspectionTemplates` is rejected and rolled back; `UPDATE ... SET
IsActive = 0` still works normally. If this ever needs undoing (e.g. a legitimate bulk-cleanup
tool), the correct approach is `DISABLE TRIGGER ... ON ...` for that one operation, not removing
the trigger.

**Two real SQL Server gotchas hit while writing the actual scripts** (not obvious from the design
doc, worth remembering for any future hand-written script against this schema — see
`AI_HANDOFF.md`'s "Important decisions" section for the fuller writeup):
1. `SET ANSI_NULLS ON` / `SET QUOTED_IDENTIFIER ON` are required in-session for any DDL or DML
   touching a table with a `PERSISTED` computed column or a filtered index — not just at table
   creation. The app's own DB driver (pyodbc/SQLAlchemy) sets these by default, but hand-written
   seed/fix scripts won't unless they say so explicitly.
2. Filtered index `WHERE` predicates don't support `NOT IN` — only `IN`, comparison operators,
   `IS NULL`/`IS NOT NULL`, and `AND`. Use `x <> a AND x <> b` instead of `x NOT IN (a, b)`.

**Interpretive design calls made while writing `09_Constraints.sql`**: the scope doc names a
"Status" field on `CleaningInspections`, `RiskAssessments`, and an "update type" on
`MaintenanceUpdates` without enumerating exact values (unlike `Inspections.Status` or
`MaintenanceIssues.Status`, which the scope spells out explicitly). Reasonable default enums were
chosen and marked `INTERPRETIVE` in the SQL comments — these are the one part of the Phase 2 SQL
that wasn't directly dictated by the scope doc, so worth a sanity check against real usage once
the app exists rather than treating them as immutable.

## 2026-08-23 — Phase 2 fully closed: seed data, views, dashboard queries, verified rebuild

Completed the rest of Phase 2 in the same session as the table/constraint/index work above:
5 roles, the full default "Monthly Property Inspection" template (21 sections, 102 questions,
built from scope's Prompt 4 - used the scope's own example questions verbatim where given, e.g.
Emergency Lighting's 5 questions, and wrote reasonable defaults for sections the scope only names
without detailing, e.g. General Property Condition, Entrance, Hallways).

**Deliberate design call on 4 "gateway" sections** (Communal Cleaning, Units, Vacant Units,
Maintenance, Risk Assessment): these carry only 1-2 checklist questions each rather than a full
question set, because their real substance already lives in dedicated tables/flows -
CleaningAreas/CleaningInspections for grading, VacantUnitInspections for vacant units,
MaintenanceIssues/RiskAssessments creatable from any question throughout the inspection.
Duplicating that detail as regular checklist questions would have fought the schema's own design
rather than complemented it. If a future session is tempted to "fill out" these sections with
more generic Yes/No questions, that's very likely a regression, not an improvement - check this
note first.

**`Users` was deliberately left unseeded.** A real `PasswordHash` needs Phase 5's actual hashing
algorithm; a fake placeholder hash would create rows that look like working demo logins but
aren't, which is worse than no demo users at all. Seed real demo users once Phase 5 exists.

**The global default risk matrix (`RiskMatrixLevels`, `CompanyId IS NULL`) was seeded as CORE
CONFIG, not demo data** - it lives in `13_SeedSampleData.sql` but in its own clearly-separated
Part A, because `RiskAssessments.RiskLevel` has nothing to snapshot from without it in ANY
environment, including production. Only Part B (the 2 demo companies) is local-dev-only. Don't
let a future "don't run seed data in production" instinct skip Part A too.

**`00_RunAll.sql` was tested for real, not just assembled**: dropped `InspectIQDb` completely
(`ALTER DATABASE ... SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE`) and rebuilt it from
nothing through the single script, then re-verified every count matched expectations. This is the
only way to actually know the file ordering and idempotency guards work together correctly - each
file having worked individually when run in sequence during development does NOT prove the
assembled `00_RunAll.sql` works, since e.g. the `RETURN`-only-exits-current-batch bug (below)
would have passed every individual-file test and only shown up on a true fresh run.

**Three more real bugs caught by actually running things, not just assumed**:
1. `SUM(CASE...)` returns `NULL` over zero rows, not `0` - every dashboard aggregate in
   `15_DashboardQueries.sql` needed `ISNULL(..., 0)`. Caught by running the queries against
   Northgate before any MaintenanceIssues/RiskAssessments/CleaningInspections existed.
2. `RETURN` in a `.sql` script only exits the current batch, not the whole script - a `GO`
   between an idempotency guard and the logic it's meant to skip silently defeats the guard.
   Caught in `12_SeedInspectionTemplate.sql` by testing re-run behavior explicitly, not assumed.
3. `Properties` has filtered indexes (`IX_Properties_NextInspectionDue`,
   `IX_Properties_PropertyStatus`), so it needs the same `ANSI_NULLS`/`QUOTED_IDENTIFIER ON`
   session settings as `RiskAssessments` does for its computed column - this wasn't obvious from
   the RiskAssessments-focused gotcha already documented above, and bit
   `13_SeedSampleData.sql`'s very first `Properties` INSERT.
