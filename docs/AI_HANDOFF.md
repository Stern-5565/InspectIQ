# AI_HANDOFF

Current status. Overwrite/update this file at the end of every session or phase — unlike
`AI_MEMORY.md`, this one should reflect the *current* state, not history.

## What has been completed

- Repo scaffolded (`backend/`, `frontend/`, `database/`, `docs/`, `prompts/`), git initialized.
- Scope document preserved (`docs/SCOPE.md`) and split into phase prompts (`prompts/`).
- **Phase 1 (Architecture) complete** — full design in `docs/PROJECT_PLAN.md`, including the
  reviewed-and-confirmed `InspectionResponse` snapshot strategy (§13.1).
- **Phase 2, step 1 (Database Design doc) complete** — 25-table design with purpose, columns,
  relationships, design decisions, and possible problems in `docs/DATABASE.md`.

## Currently being worked on

- Nothing in progress. `docs/DATABASE.md` is written but not yet reviewed by the owner. Phase 2,
  step 2 (actual SQL Server schema files under `database/`, per `prompts/database_prompt.md`
  Prompt 3, one file at a time) is next.

## Important decisions

See `docs/AI_MEMORY.md` for the reasoning behind each; summarized in `docs/PROJECT_PLAN.md` and
`docs/DATABASE.md §9`.

## Known bugs

None — no code exists yet.

## Database structure

Designed but not yet implemented as SQL — see `docs/DATABASE.md` for the full 25-table design.
Two structural requirements carried over from the Phase 1 sign-off and **must** appear in the
actual SQL: soft-delete-only enforcement (no `DELETE`) on `InspectionQuestions`/`Sections`/
`Templates`, and `InspectionTemplate.Version` + `Inspections.TemplateVersionUsed`. `RiskScore` on
`RiskAssessments` must be a computed column (`AS (Likelihood * Severity) PERSISTED`), not a plain
insertable column — this is a Phase 2 SQL requirement, not optional polish.

## Coding standards

Not yet established in code — see `docs/PROJECT_PLAN.md §5–6` for the intended backend/frontend
layering rules (routes thin, services own business logic, repositories own DB access).

## Next tasks

Phase 2, step 2 — generate the actual T-SQL under `database/`, file by file, per the plan at the
end of `docs/DATABASE.md` (`00_CreateDatabase.sql`, then `tables/01_CoreTables.sql` through
`tables/08_NotificationAuditTables.sql`, then constraints/indexes/seed/views/reports). Explain
each file, generate the SQL, explain its constraints, give test queries — per Prompt 3's own
pacing rule.

## Files that require attention

- `docs/DATABASE.md §10.1` (denormalized `CompanyId` drift risk) and `§10.4` (plaintext
  alarm/access codes) are real, not-yet-mitigated risks — worth remembering when writing the
  actual repository code in later phases, not just the SQL.
