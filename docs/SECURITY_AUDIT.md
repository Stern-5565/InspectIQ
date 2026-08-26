# Phase 19 — Cross-Company Security Audit

Dedicated audit per `PROJECT_PLAN.md §11`'s 20-phase table ("Phase 19 | Security | Cross-company
isolation explicitly verified"). Distinct from [Phase 18](AI_MEMORY.md)'s adversarial testing
pass, which found and fixed a real concurrency bug but verified isolation only incidentally (a
10-endpoint sweep against a *nonexistent* ID). This phase verifies isolation against **real
records genuinely owned by a different real company** — the guarantee that actually matters for
a multi-tenant system — and makes the two decisions `docs/DATABASE.md §10` explicitly deferred to
"a Phase 19 review."

## Methodology

1. **Static review**: read every route in `backend/app/api/*.py` (60+ endpoints across 16
   routers) and confirmed each one depends on `get_current_user` or `require_roles` — no
   unauthenticated route exists except `/auth/login`, `/auth/refresh`, and `/health`, all
   correctly public.
2. **Static review**: read every repository function in `backend/app/repositories/*.py` and
   confirmed every query touching company-scoped data filters by `company_id` — either directly
   (tables with their own `CompanyId` column) or via a join through `Property`/`Inspection`
   (tables without one). No repository function trusts a bare ID without a company filter.
3. **Static review**: grepped every service file for `CompanyId=` (the only place a new record's
   `CompanyId` is ever set) and confirmed all six write sites — `maintenance_service.py`,
   `media_service.py`, `property_service.py`, `risk_service.py` (×2), `user_service.py` — assign
   it from `current_user.CompanyId`, never from client input or any other source. This directly
   resolves `docs/DATABASE.md §10.1`'s flagged drift risk for the denormalized `CompanyId` columns
   on `MaintenanceIssues`/`RiskAssessments`/`MediaFiles`.
4. **Empirical verification**: new `backend/tests/test_security_audit.py`. Builds one full
   "universe" of real records spanning every entity type this app exposes (Property, Unit,
   CleaningArea, Inspection + response, MaintenanceIssue, RiskAssessment, CleaningInspection,
   VacantUnitInspection, MeterReading, MediaFile), all genuinely owned by Northgate Property
   Management, created through real HTTP calls. Then, as a genuine Bright Spaces Estates
   Administrator:
   - Attempts to **read or mutate** all 30 of those real records across every relevant endpoint —
     every single one 404s, never 403 (the project's standing "indistinguishable from
     nonexistent" rule, unbroken).
   - Attempts to **create a child record** under six of Northgate's real parents (a unit under
     their property, a cleaning grade under their inspection, a maintenance issue against their
     property, etc.) — every attempt 404s before any row is written.
   - Confirms the denormalized `CompanyId` on every created record matches its parent's company
     exactly (empirical proof for the static-review finding in step 3).

   6 new tests, all passing against the real DB. Combined with Phase 18, 194 backend tests total.

## Findings

### Resolved: denormalized `CompanyId` drift (`DATABASE.md §10.1`)

No drift risk found, confirmed both statically (every write site) and empirically (every created
record's `CompanyId` matches its parent). This item is closed — no code change was needed, only
verification, which is exactly what `§10.1` asked Phase 19 to do.

### Open decision needed: `Property.AlarmAccessCode` (`DATABASE.md §10.4`)

`§10.4` flagged this as needing "a deliberate Phase 19/20 decision, not an oversight." Two
separate issues, found by reading `PropertyResponse` (`app/schemas/property.py`) and
`properties.py`'s own route gating:

1. **Stored in plain text** in `Properties.AlarmAccessCode` — no encryption at rest, no
   field-level encryption.
2. **Visible to every company role**, including Viewer — `GET /api/properties/{id}` is
   view-level auth (any authenticated company member), the same tier as every other property
   field. A physical alarm/door code is a materially different sensitivity class than
   `PropertyName` or `Postcode`, but the API doesn't currently distinguish them.

Not fixed in this pass — this is a real product/scope decision, not just a code fix, since some
roles (e.g. Maintenance workers who need physical access) plausibly *do* need this code as part
of their job, while others (Viewer) plausibly don't. `report_service.py` already deliberately
excludes `AlarmAccessCode` from the PDF report (a narrower, already-made call), and the frontend
already masks it behind a password-toggle as a cosmetic mitigation (Phase 16) — but the raw value
still round-trips through the API to any company member today.

**Options, roughly cheapest to most work:**
- Leave as-is, documented as an accepted risk for the demo/pre-launch stage (matches how
  PropertyManager's own JWT secret placeholder was handled before its production hardening pass).
- Restrict `AlarmAccessCode` visibility in `PropertyResponse` to Administrator/Manager only (a
  narrower response schema or a conditional field), independent of encryption.
- Encrypt at rest (application-level field encryption, decrypted only on the narrowed-visibility
  path above) — the real fix if this ever becomes commercial SaaS handling real customers' door
  codes, per `§10.4`'s own framing.

### Minor, accepted: cross-company email-existence oracle (consequence of `DATABASE.md §10.2`)

`user_service.create_user` checks email uniqueness globally (`user_repository.get_user_by_email`,
no company filter — correct, since `Users.Email` is a real global-unique DB constraint, `§10.2`'s
own already-documented tradeoff). The practical side effect: an Administrator at Company A can
learn whether an arbitrary email is already registered *anywhere*, including at a competitor
company, via the "A user with this email already exists" `409` on `POST /api/users`. Low
severity — it requires an authenticated Administrator (not an anonymous prober), and email
existence alone leaks no other data. Noted as a documented consequence of an already-accepted
tradeoff, not a new independent gap; not changed in this pass.

### Informational: three schema tables have zero application code

`Notes`, `Notifications`, and `AuditLogs` exist as real tables (`docs/DATABASE.md §7`, Phase 2)
but have no model, service, repository, or route anywhere in `backend/app/` — confirmed by
searching the whole backend tree. No isolation risk currently exists for them simply because
nothing reads or writes them yet. Worth re-auditing whenever one of them gets a real
implementation, not before.

### Informational: no login rate-limiting

`POST /api/auth/login` has no attempt throttling. Not a regression from anything — no rate
limiting has existed at any phase — but worth naming explicitly now that a dedicated security
pass exists, as a candidate for Phase 20 (deployment) hardening alongside real infra concerns
(HTTPS termination, `APP_DEBUG=False` in production, the JWT secret guard already built in
Phase 4).

## What Phase 19 deliberately did not re-litigate

Every module's own per-file tests already cover role-based authorization (Admin-vs-Manager-vs-
Inspector tiers) exhaustively — that's a different guarantee from company isolation and wasn't
the target of this pass. Phase 18 already covered token forgery, mass-assignment, and injection
safety. This phase's job was specifically: does a real record ever leak or accept writes across
a company boundary — and per the findings above, no, with two decisions still open for the owner.
