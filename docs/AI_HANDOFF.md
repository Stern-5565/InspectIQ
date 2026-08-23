# AI_HANDOFF

Current status. Overwrite/update this file at the end of every session or phase — unlike
`AI_MEMORY.md`, this one should reflect the *current* state, not history.

## What has been completed

- Repo scaffolded (`backend/`, `frontend/`, `database/`, `docs/`, `prompts/`), git initialized.
- Scope document preserved (`docs/SCOPE.md`) and split into phase prompts (`prompts/`).
- **Phase 1 (Architecture) complete** — full design in `docs/PROJECT_PLAN.md`, including the
  reviewed-and-confirmed `InspectionResponse` snapshot strategy (§13.1).
- **Phase 2 (Database Design + full SQL) complete**, verified against a real local SQL Server
  instance (`localhost\SQLEXPRESS`, database `InspectIQDb`, Windows auth) — every layer, not just
  the table shapes:
  - `docs/DATABASE.md` — the 25-table design doc.
  - `database/00_CreateDatabase.sql`, `database/tables/01`–`08` — all 25 tables.
  - `database/constraints/09_Constraints.sql` — every enum `CHECK` constraint, plus 3
    `INSTEAD OF DELETE` triggers making the Phase 1 soft-delete-only requirement a real DB
    guarantee, not just a documented convention.
  - `database/indexes/10_Indexes.sql` — 43 non-clustered indexes.
  - `database/seed/11_SeedRoles.sql` (5 roles), `12_SeedInspectionTemplate.sql` (the Monthly
    Property Inspection template — 21 sections, 102 questions, per scope Prompt 4),
    `13_SeedSampleData.sql` (global default risk matrix as core config + 2 demo companies/4
    properties/11 units as local-dev-only data — `Users` deliberately NOT seeded yet, see below).
  - `database/views/14_InspectionViews.sql` — 5 reusable views (`vw_InspectionSummary`,
    `vw_OverdueInspections`, `vw_OpenMaintenanceIssues`, `vw_ActiveRiskAssessments`,
    `vw_PropertyUnitCounts`).
  - `database/reports/15_DashboardQueries.sql` — every scope §23 dashboard metric as a
    standalone, company-scoped, `ISNULL`-safe query, ready to lift into `DashboardRepository`
    in Phase 15.
  - `database/scripts/00_RunAll.sql` — **tested for real**: dropped `InspectIQDb` entirely and
    rebuilt it from nothing via this one script, then re-verified every count (25 tables, 5
    roles, 21 sections/102 questions, 2 companies/4 properties, 4 risk levels, 43 indexes, 3
    triggers, 5 views). It genuinely works end-to-end, not just "each file worked in isolation."

## Currently being worked on

- Nothing in progress. Committing this batch to git is the next action, then Phase 2 is fully
  closed and Phase 3/4 (which the scope's 20-phase list treats as blending into FastAPI
  foundation work) is next.

## Important decisions

See `docs/AI_MEMORY.md` for the reasoning behind each; summarized in `docs/PROJECT_PLAN.md` and
`docs/DATABASE.md §9`. Real gotchas discovered while writing the actual SQL (not previously
documented, worth knowing for any future script against this schema):

1. **Any statement that creates or writes to a table with a `PERSISTED` computed column
   (`RiskAssessments.RiskScore`) OR a filtered index (`Properties.NextInspectionDue`,
   `Properties.PropertyStatus`, `MaintenanceIssues.DueDate`) needs `SET ANSI_NULLS ON` and
   `SET QUOTED_IDENTIFIER ON` in that session first**, or SQL Server rejects it (`Msg 1934`) —
   this bit `13_SeedSampleData.sql` on a plain `Properties` INSERT, not just `RiskAssessments`.
   SQLAlchemy/pyodbc set these by default, so the application itself won't hit this — but any
   hand-written script will.
2. **Filtered index predicates don't support `NOT IN`** (`Msg 102`) — use
   `x <> a AND x <> b` instead of `x NOT IN (a, b)`.
3. **`SUM(CASE...)` over zero matching rows returns `NULL`, not `0`.** Caught by actually
   running `15_DashboardQueries.sql` against a company with no maintenance/risk/cleaning data
   yet — every dashboard aggregate is wrapped in `ISNULL(..., 0)` as a result. A dashboard card
   must never render `NULL` as if it were an empty state.
4. **`RETURN` inside a `.sql` script only exits the current batch, not the whole script.** An
   idempotency guard (`IF EXISTS (...) BEGIN ... RETURN; END`) must be in the *same batch* as
   the logic it's meant to skip — a `GO` between the guard and the inserts silently defeats it.
   Caught in `12_SeedInspectionTemplate.sql` before it caused a real duplicate-data bug.

## Known bugs

None. The schema (tables, constraints, triggers, indexes, seed data, views, dashboard queries)
is fully implemented and verified — including a from-scratch rebuild via `00_RunAll.sql`. No
application code exists yet.

## Database structure

Fully implemented — see `docs/DATABASE.md` for the design, `database/` for the SQL, all applied
and verified against a real local `InspectIQDb`. Both structural requirements from the Phase 1
sign-off are live and trigger-enforced. `RiskAssessments.RiskScore` is a verified-working
`PERSISTED` computed column. The default inspection template (21 sections/102 questions) and
global risk matrix are seeded; 2 demo companies with realistic property/unit data exist locally.

## Coding standards

Not yet established in code — see `docs/PROJECT_PLAN.md §5–6` for the intended backend/frontend
layering rules (routes thin, services own business logic, repositories own DB access).

## Next tasks

1. Commit this batch (seed/views/reports/00_RunAll.sql) to git.
2. Phase 4 — FastAPI foundation (`prompts/backend_prompt.md`, Prompt 5): app skeleton, config,
   DB connection (SQLAlchemy models mapping to this exact schema), health-check endpoint.
3. **`Users` still needs seeding once Phase 5 (Authentication) exists** and can produce a real
   password hash — don't seed fake-hash demo users before then (see `13_SeedSampleData.sql`'s
   header comment for the reasoning).

## Files that require attention

- `docs/DATABASE.md §10.1` (denormalized `CompanyId` drift risk) and `§10.4` (plaintext
  alarm/access codes) are real, not-yet-mitigated risks — worth remembering when writing the
  actual repository code in later phases, not just the SQL.
- Several `CHECK` constraints in `09_Constraints.sql` are marked `INTERPRETIVE` in comments
  (`Properties.PropertyStatus`, `CleaningInspections.Status`, `MaintenanceUpdates.UpdateType`,
  `RiskAssessments.Status`) — the scope doc mentions these fields without enumerating exact
  values, so a reasonable default list was chosen. Worth a quick sanity check against real usage
  once the app exists, not treated as scope-mandated.
