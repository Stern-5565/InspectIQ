# AI_HANDOFF

Current status. Overwrite/update this file at the end of every session or phase — unlike
`AI_MEMORY.md`, this one should reflect the *current* state, not history.

## What has been completed

- Repo scaffolded (`backend/`, `frontend/`, `database/`, `docs/`, `prompts/`), git initialized.
- Scope document preserved (`docs/SCOPE.md`) and split into phase prompts (`prompts/`).
- **Phase 1 (Architecture) complete** — full design in `docs/PROJECT_PLAN.md`. No code written
  yet, by design (scope's own "do not write the application yet" instruction for this phase).

## Currently being worked on

- Nothing in progress. `docs/PROJECT_PLAN.md` §13.1 reviewed and confirmed by the owner
  (2026-08-23) — frozen-column snapshot strategy, with soft-delete-only on InspectionQuestions and
  a Version/TemplateVersionUsed counter as mandatory additions. Phase 1 is fully signed off.
  Phase 2 (Database Design) is next and unblocked.

## Important decisions

See `docs/AI_MEMORY.md` for the reasoning behind each; summarized in `docs/PROJECT_PLAN.md`.

## Known bugs

None — no code exists yet.

## Database structure

Not yet designed (Phase 2, next).

## Coding standards

Not yet established in code — see `docs/PROJECT_PLAN.md` §5–6 for the intended backend/frontend
layering rules (routes thin, services own business logic, repositories own DB access).

## Next tasks

Phase 2 — Database Design (`prompts/database_prompt.md`, Prompt 2): list every table with purpose/
relationships/design decisions/possible problems, then generate SQL Server schema files under
`database/`. Must include the two mandatory additions from the §13.1 sign-off: soft-delete-only
enforcement on InspectionQuestions/Sections/Templates, and `InspectionTemplate.Version` +
`Inspections.TemplateVersionUsed` columns.

## Files that require attention

None yet.
