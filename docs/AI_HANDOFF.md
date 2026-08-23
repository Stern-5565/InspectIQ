# AI_HANDOFF

Current status. Overwrite/update this file at the end of every session or phase — unlike
`AI_MEMORY.md`, this one should reflect the *current* state, not history.

## What has been completed

- Repo scaffolded (`backend/`, `frontend/`, `database/`, `docs/`, `prompts/`), git initialized.
- Scope document preserved (`docs/SCOPE.md`) and split into phase prompts (`prompts/`).
- **Phase 1 (Architecture) complete** — full design in `docs/PROJECT_PLAN.md`, including the
  reviewed-and-confirmed `InspectionResponse` snapshot strategy (§13.1).
- **Phase 2, step 1 (Database Design doc) complete** — 25-table design in `docs/DATABASE.md`.
- **Phase 2, step 2 (actual SQL) mostly complete and verified against a real local SQL Server
  instance** (`localhost\SQLEXPRESS`, database `InspectIQDb`, Windows auth):
  - `database/00_CreateDatabase.sql` — done.
  - `database/tables/01_CoreTables.sql` through `08_NotificationAuditTables.sql` — all 25 tables
    created. One deferred FK (`MeterReadings.PhotoMediaFileId` → `MediaFiles`) added via
    `ALTER TABLE` in `07_MediaAndNotesTables.sql` once `MediaFiles` exists.
  - `database/constraints/09_Constraints.sql` — every enum `CHECK` constraint, plus three
    `INSTEAD OF DELETE` triggers that make the Phase 1 soft-delete-only requirement a real DB
    guarantee (blocks hard deletes on `InspectionTemplates`/`Sections`/`Questions`), not just a
    documented convention.
  - `database/indexes/10_Indexes.sql` — 43 non-clustered indexes covering every realistically
    filtered/joined FK column plus the Dashboard module's query patterns (scope §23).
  - Two throwaway verification scripts under `database/scripts/` (`test_01_02_verify.sql`,
    `test_09_constraints_verify.sql`) exercise the constraints/triggers against real data and
    clean up after themselves — all assertions passed.

## Currently being worked on

- Nothing in progress. Not yet committed to git as of this note being written — do that next,
  then continue with seed data (`seed/11_SeedRoles.sql`, `12_SeedInspectionTemplate.sql`,
  `13_SeedSampleData.sql`), then views/reports/`00_RunAll.sql`.

## Important decisions

See `docs/AI_MEMORY.md` for the reasoning behind each; summarized in `docs/PROJECT_PLAN.md` and
`docs/DATABASE.md §9`. Two real gotchas discovered while writing the actual SQL (not previously
documented, worth knowing for any future script against this schema):

1. **Any statement that creates or writes to a table with a `PERSISTED` computed column
   (`RiskAssessments.RiskScore`) or a filtered index needs `SET ANSI_NULLS ON` and
   `SET QUOTED_IDENTIFIER ON` in that session first**, or SQL Server rejects it (`Msg 1934`).
   SQLAlchemy/pyodbc set these by default, so the application itself won't hit this — but any
   hand-written script (seed data, ad hoc fixes) will, and did during this session.
2. **Filtered index predicates don't support `NOT IN`** (SQL Server parser rejects it,
   `Msg 102`) — `IX_MaintenanceIssues_DueDate` originally tried
   `WHERE Status NOT IN ('Completed', 'Closed')` and had to be rewritten as
   `WHERE Status <> 'Completed' AND Status <> 'Closed'` (two comparisons ANDed, which the
   filtered-index predicate grammar does support).

## Known bugs

None — no application code exists yet. The schema itself is verified working (constraints,
triggers, and the computed column all behave correctly under real test inserts).

## Database structure

Fully implemented, not just designed — see `docs/DATABASE.md` for the design and
`database/tables/`, `database/constraints/`, `database/indexes/` for the actual SQL, all applied
to a real local `InspectIQDb`. Both structural requirements from the Phase 1 sign-off are live:
soft-delete-only (enforced by trigger, not just convention) and
`InspectionTemplate.Version`/`Inspections.TemplateVersionUsed`. `RiskAssessments.RiskScore` is a
verified-working `PERSISTED` computed column.

## Coding standards

Not yet established in code — see `docs/PROJECT_PLAN.md §5–6` for the intended backend/frontend
layering rules (routes thin, services own business logic, repositories own DB access).

## Next tasks

1. Commit the current SQL (tables/constraints/indexes) to git.
2. Seed data: `seed/11_SeedRoles.sql` (5 roles), `seed/12_SeedInspectionTemplate.sql` (the
   Monthly Property Inspection template from Prompt 4 — not yet written, needs its own pass
   through `prompts/database_prompt.md`'s Prompt 4 text), `seed/13_SeedSampleData.sql` (demo
   companies/properties/users for local dev, same spirit as PropertyManager's
   `06-seed-demo-data.sql` but nothing in production per that project's own lesson).
3. `views/14_InspectionViews.sql`, `reports/15_DashboardQueries.sql`.
4. `scripts/00_RunAll.sql` once every file above exists.
5. Then Phase 3 (sample data + SQL queries) blends into Phase 4 (FastAPI foundation).

## Files that require attention

- `docs/DATABASE.md §10.1` (denormalized `CompanyId` drift risk) and `§10.4` (plaintext
  alarm/access codes) are real, not-yet-mitigated risks — worth remembering when writing the
  actual repository code in later phases, not just the SQL.
- Several `CHECK` constraints in `09_Constraints.sql` are marked `INTERPRETIVE` in comments
  (`Properties.PropertyStatus`, `CleaningInspections.Status`, `MaintenanceUpdates.UpdateType`,
  `RiskAssessments.Status`) — the scope doc mentions these fields without enumerating exact
  values, so a reasonable default list was chosen. Worth a quick sanity check against real usage
  once the app exists, not treated as scope-mandated.
