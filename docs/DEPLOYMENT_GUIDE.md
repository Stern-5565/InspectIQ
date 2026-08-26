# InspectIQ — Deployment Guide (Phase 20)

Mirrors the architecture and checklist discipline of PropertyManager's own deployment
(`property-management-system/documentation/deployment-guide.md`) — same Azure footprint, same
"pause before each real provisioning step, no unattended run" approach the owner explicitly
chose there. One genuine difference: InspectIQ has real file uploads (photos/videos), so it
needs a storage tier PropertyManager never did — Azure Blob Storage, already built in
`app/services/media_storage.py`'s `AzureBlobStorageService` and gated behind one setting,
`MEDIA_STORAGE_PROVIDER`.

**Nothing has been provisioned in Azure yet.** This document is the plan; each step below still
needs individual confirmation before it runs, exactly like PropertyManager's Prompt 31 — real
resources cost real money and are visible outside this machine, so this isn't something to run
unattended top to bottom.

---

## 1. Recommended deployment architecture

| Layer | Choice | Why |
|---|---|---|
| Database | Azure SQL, serverless, free-limit offer | Same offer PropertyManager used — genuinely $0/month at this traffic (`--use-free-limit --free-limit-exhaustion-behavior AutoPause`). |
| Backend | Azure Container Apps (consumption plan) | pyodbc needs the Microsoft ODBC driver as a system package, which rules out App Service's stock Python runtime — same reason PropertyManager landed on Container Apps over its originally-planned App Service. Consumption plan is genuinely $0/month at this traffic (`min-replicas 0`). |
| Container registry | Azure Container Registry (Basic tier) | ~$5/month — the one paid resource in this stack, same as PropertyManager's. |
| Media storage | Azure Blob Storage (Standard, LRS) | New for this project — PropertyManager had no file uploads. Pennies/month at this scale (pay-per-GB + per-operation, no fixed tier). Container access level must be **Private** — never Blob/Container anonymous read (see `media_storage.py`'s own docstring on why: a public blob URL would bypass every per-request permission check this app is built around). |
| Frontend | Azure Static Web Apps (Free tier) | Same as PropertyManager. |

Resource naming (avoiding collision with PropertyManager's existing resources in the same
subscription — `pm-*`/`propertymanager-*`):

- Resource group: `inspectiq-rg`
- SQL server: `inspectiq-sql-shmuelstern`, database `InspectIQDb`
- Container Registry: `inspectiqacrshmuelstern` (must be globally unique, alphanumeric only)
- Container Apps environment: `inspectiq-env`, app `inspectiq-api`
- Storage account: `inspectiqstorageshm` (globally unique, lowercase alphanumeric, 3–24 chars),
  container `media`
- Static Web App: `inspectiq-web`

---

## 2. Production database setup

1. `az group create --name inspectiq-rg --location uksouth`
2. `az sql server create --name inspectiq-sql-shmuelstern --resource-group inspectiq-rg --location uksouth --admin-user inspectiqadmin --admin-password <generated>` — save the password to a local scratch file outside the repo, never in chat/git, same convention as PropertyManager's `pmadmin` credential.
3. `az sql db create --resource-group inspectiq-rg --server inspectiq-sql-shmuelstern --name InspectIQDb --use-free-limit --free-limit-exhaustion-behavior AutoPause`
4. Add a firewall rule allowing Azure services (`--allow-azure-ip` or the "Allow Azure services" checkbox).
5. Run `database/00_CreateDatabase.sql` through `database/seed/11_SeedRoles.sql` and
   `12_SeedInspectionTemplate.sql` against the new server via `sqlcmd` — **deliberately NOT**
   `13_SeedSampleData.sql` (no demo companies/properties in production) and **deliberately NOT**
   `backend/scripts/seed_demo_users.py` (no `Password123!` accounts in production — the exact
   rule PropertyManager's deployment followed). `14_InspectionViews.sql` and
   `15_DashboardQueries.sql` aren't needed — Phase 15 already lifted their logic into
   `dashboard_repository.py`'s SQLAlchemy Core, the raw SQL files were reference material only.
6. Run `09_Constraints.sql`, `10_Indexes.sql` — every table/constraint/index/trigger, same as
   local dev's `00_RunAll.sql` does, just against the real server instead of `sqlcmd` local auth.

---

## 3. Backend deployment

1. `az acr create --resource-group inspectiq-rg --name inspectiqacrshmuelstern --sku Basic`
2. `az acr build --registry inspectiqacrshmuelstern --image inspectiq-backend:v1 backend/` — remote build,
   no local Docker needed (confirmed working for PropertyManager's identical Dockerfile
   pattern). `backend/Dockerfile` already exists (Phase 20 repo-prep, done) — bakes in the
   `msodbcsql18`/`libgssapi-krb5-2` fix from the start rather than rediscovering it live the way
   PropertyManager's session had to.
3. `az containerapp env create --name inspectiq-env --resource-group inspectiq-rg --location uksouth`
4. `az containerapp create` with:
   - System-assigned Managed Identity + `AcrPull` role on `inspectiqacrshmuelstern` (no shared registry
     login, same as PropertyManager).
   - Secrets (Container Apps' own encrypted secret store): `db-password`,
     `jwt-secret-key` (fresh, `python -c "import secrets; print(secrets.token_urlsafe(64))"`),
     `azure-storage-connection-string`.
   - Environment variables: `APP_ENV=production`, `APP_DEBUG=false`, `DB_SERVER=inspectiq-sql-shmuelstern.database.windows.net`, `DB_NAME=InspectIQDb`, `DB_DRIVER=ODBC Driver 18 for SQL Server`, `DB_TRUSTED_CONNECTION=false`, `DB_USER=inspectiqadmin`, `DB_PASSWORD=secretref:db-password`, `JWT_SECRET_KEY=secretref:jwt-secret-key`, `CORS_ALLOWED_ORIGINS=<frontend URL, set after step 4 below>`, `MEDIA_STORAGE_PROVIDER=azure_blob`, `AZURE_STORAGE_CONNECTION_STRING=secretref:azure-storage-connection-string`, `AZURE_STORAGE_CONTAINER_NAME=media`.
   - `--target-port 8000 --ingress external`.
5. Configure a liveness probe against `/api/health` — PropertyManager's own audit
   (`propertymanager-status` memory) found this was never actually wired up despite the endpoint
   working correctly; don't repeat that gap here, set it explicitly during creation.

---

## 4. Media storage setup (new for this project)

1. `az storage account create --name inspectiqstorageshm --resource-group inspectiq-rg --location uksouth --sku Standard_LRS`
2. `az storage container create --name media --account-name inspectiqstorageshm --public-access off` — **`off` is not optional**, see §1's note on why a public container would defeat this app's whole permission model.
3. `az storage account show-connection-string --name inspectiqstorageshm --resource-group inspectiq-rg` → store as the `azure-storage-connection-string` Container Apps secret (step 3.4 above).
4. No data migration needed — a fresh production deployment starts with zero `MediaFiles` rows, same as it starts with zero `Users`/`Properties` rows.

---

## 5. Frontend deployment

1. `frontend/.env.production` already exists (Phase 16) with `VITE_CSP_STYLE_SRC="'self'"`. Add
   the real backend origin: `VITE_API_BASE_URL=https://<container-app-fqdn>/api`,
   `VITE_API_ORIGIN=https://<container-app-fqdn>` — **must be set at `npm run build` time**,
   not runtime (Vite bakes env vars into the built bundle).
2. `az staticwebapp create --name inspectiq-web --resource-group inspectiq-rg --location westeurope` — West Europe, not UK South, same hard platform constraint PropertyManager hit (Static Web Apps only supports a short region list).
3. `npm run build` then deploy via SWA CLI + deployment token (manual, not GitHub Actions — same reasoning as PropertyManager: interactive GitHub OAuth isn't completable in this session).
4. `frontend/public/staticwebapp.config.json` needs a `navigationFallback` rule for SPA routing — PropertyManager's deployment found direct navigation to any non-root route 404s from Static Web Apps without this. **Confirm this file exists in InspectIQ's `frontend/public/` before first deploy** — check now, don't rediscover live.

---

## 6. CORS configuration

`CORS_ALLOWED_ORIGINS` (Container Apps env var) must be set to the real Static Web Apps origin
once step 5.2 produces it — a circular dependency with step 3 resolved the same way
PropertyManager resolved it: deploy the backend first with a placeholder/localhost CORS origin,
deploy the frontend, then update the backend's `CORS_ALLOWED_ORIGINS` env var to the real
frontend URL and let Container Apps restart with it.

---

## 7. HTTPS requirements

Both Container Apps and Static Web Apps provide HTTPS by default on their own subdomains (no
extra configuration needed, same as PropertyManager's deployment). A custom domain would need
its own certificate — out of scope unless the owner wants one.

---

## 8. CSP

`frontend/index.html`'s CSP `<meta>` tag already exists (Phase 16, built in from the start —
unlike PropertyManager, which deferred it to the deployment phase and had to retrofit it).
`connect-src` needs `VITE_API_ORIGIN` substituted at build time exactly like PropertyManager's
CSP did — **exact-match path requirement**: `VITE_API_ORIGIN` must be the origin only (no
`/api` suffix), a separate variable from `VITE_API_BASE_URL`, or CSP will silently block every
real API call with no console/network error (PropertyManager's own hard-won bug, avoid
reproducing it — `frontend/.env.example` already documents this distinction).

---

## 9. Environment variables — full reference

Backend (Container Apps secrets/env vars): `APP_ENV`, `APP_DEBUG`, `JWT_SECRET_KEY`,
`JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`, `DB_SERVER`,
`DB_NAME`, `DB_DRIVER`, `DB_TRUSTED_CONNECTION`, `DB_USER`, `DB_PASSWORD`,
`CORS_ALLOWED_ORIGINS`, `MEDIA_STORAGE_PROVIDER`, `AZURE_STORAGE_CONNECTION_STRING`,
`AZURE_STORAGE_CONTAINER_NAME`. Full defaults/validation logic in `app/core/config.py`.

Frontend (build-time only, `.env.production`): `VITE_API_BASE_URL`, `VITE_API_ORIGIN`,
`VITE_CSP_STYLE_SRC`.

---

## 10. Database migration process

No migration framework exists (Alembic etc.) — schema changes since Phase 2 have all been
additive SQL scripts run once. For this first deployment, running `database/00`–`10` and the two
non-demo seed scripts (§2 above) IS the migration. Future schema changes would need a real
migration story decided before they happen — not yet needed, no schema change has occurred
since Phase 2.

---

## 11. Demo data process

**None in production.** Local dev's `13_SeedSampleData.sql` (2 demo companies) and
`backend/scripts/seed_demo_users.py` (`Password123!` accounts) must never run against the
production database — same absolute rule PropertyManager followed (0 rows in `Users` until a
real Administrator account is created manually, §14 below).

---

## 12. Logging

`app/core/logging_config.py` already exists (Phase 4) — Container Apps captures stdout/stderr
automatically via `az containerapp logs show`, no extra wiring needed.

---

## 13. Health checks

`GET /api/health` (Phase 4) genuinely queries the DB, not a stub. Wire it as the Container Apps
liveness probe explicitly during creation (§3.5) — don't leave this implicit the way
PropertyManager's deployment did.

---

## 14. Backup considerations

Azure SQL's serverless free-limit tier includes automatic point-in-time backups by default (7-day
retention on Basic-equivalent tiers) — no extra configuration needed for this scale. Blob
Storage has no automatic backup at Standard_LRS (locally-redundant only, no geo-replication) —
acceptable for this project's current scale; revisit if this ever becomes real commercial SaaS
per `PROJECT_PLAN.md`'s own scalability notes.

---

## 15. Rollback plan

Container Apps supports revision-based rollback (`az containerapp revision list` /
`az containerapp ingress traffic set` to shift traffic back to a prior revision) — no extra setup
needed, it's inherent to how Container Apps deploys. Static Web Apps: redeploy the previous
build via SWA CLI (no auto-versioning without GitHub Actions, which isn't wired up — same gap
PropertyManager left as a deliberately-deferred follow-up).

---

## 16. Post-deployment testing checklist

Walk through live, through the actual browser against the real deployed URLs, not curl alone
(same discipline every phase of this project has held itself to):

- [ ] `GET /api/health` returns `{"status":"ok","database":"connected"}` against the real DB.
- [ ] Create the real Administrator account (own email, generated password — never in chat/git,
      same scratch-file convention as PropertyManager's credentials) via a one-off script using
      the app's own `hash_password`, same pattern as `seed_demo_users.py` but for exactly one
      real user.
- [ ] Log in through the real deployed frontend with that account.
- [ ] Create a real Company profile, a real Property, a real Unit.
- [ ] Start a real inspection, answer questions, upload a real photo — confirm it round-trips
      through Azure Blob Storage (not just that the upload returns 201 — download it back and
      confirm the bytes match, the exact check Phase 9's own local-storage verification used).
- [ ] Submit the inspection, download the generated PDF report, confirm the photo is embedded.
- [ ] Confirm direct navigation to a non-root frontend route (e.g. a hard refresh on
      `/properties`) doesn't 404 — the exact SPA-routing gap PropertyManager's deployment found.
- [ ] Confirm CORS+CSP+backend+DB all work together: a deliberate wrong-password login attempt
      through the real UI returns the backend's actual "Incorrect email or password." message,
      not a silent `TypeError: Failed to fetch` (CSP's signature failure mode if
      `VITE_API_ORIGIN` is wrong).
- [ ] Confirm `APP_DEBUG=false` in production (no SQL/PII in logs).
- [ ] Confirm the JWT secret guard actually fired during startup if a placeholder was ever
      accidentally left in — check Container Apps' startup logs for a clean boot, no
      `ValueError`.

---

## Execution order (pause before each numbered step for explicit confirmation — no unattended run)

1. ~~Repo prep~~ — done: `backend/Dockerfile`, `.dockerignore`, `AzureBlobStorageService` +
   `MEDIA_STORAGE_PROVIDER` setting, `azure-storage-blob` dependency, tests for the new
   fail-fast config guard, `frontend/public/staticwebapp.config.json` (closing the SPA-routing
   gap PropertyManager only found live in production - proactively fixed here instead). All
   free, local, reversible — no Azure resources touched yet. **`backend/Dockerfile` itself is
   NOT build-tested** — Docker CLI is present on this machine but its daemon isn't running
   (same situation PropertyManager's session hit), so the actual first build test happens via
   `az acr build` in step 3 below (a remote build, needs no local Docker) — exactly how
   PropertyManager's own Dockerfile got its first real build test.
2. ~~Provision the resource group + Azure SQL~~ — **done, 2026-08-26**: `inspectiq-rg`
   (UK South), SQL server `inspectiq-sql-shmuelstern` (admin `inspectiqadmin`, generated
   password saved to a local scratch file outside the repo, never in chat/git — same convention
   PropertyManager's `pmadmin` credential used; recoverable via `az sql server update
   --admin-password` if lost), database `InspectIQDb` on the free-limit serverless offer
   (needed `--edition GeneralPurpose --family Gen5 --capacity 2 --compute-model Serverless`
   explicitly — the bare `--use-free-limit` flag alone errored with `ProvisioningDisabled`, not
   documented this precisely in PropertyManager's own notes, now captured here for next time).
   Firewall rules added for Azure services (`0.0.0.0`/`0.0.0.0`, the standard "allow Azure
   services" convention) and this dev machine's own IP (for running the schema scripts via
   `sqlcmd` from here). Ran `tables/01`–`08`, `constraints/09`, `indexes/10`,
   `seed/11_SeedRoles.sql`, `seed/12_SeedInspectionTemplate.sql`, and Part A only of
   `seed/13_SeedSampleData.sql` (the global risk matrix — extracted to a temp production-only
   script, Part B's demo companies deliberately excluded). **Verified with real row counts
   against the live Azure DB, not just "the script ran"**: 25 tables, 5 roles, 1 template/21
   sections/102 questions, 4 risk matrix levels, 3 triggers, 22 CHECK constraints — and
   `Companies`/`Users`/`Properties` all genuinely 0, confirming no demo data leaked in.
3. ~~Provision ACR + build/push the backend image~~ — **done, 2026-08-26**: `inspectiqacrshmuelstern`
   was already taken globally (ACR names are global across all Azure customers, not just this
   subscription) — used `inspectiqacrshmuelstern` instead, same naming-collision pattern the
   SQL server name already accounted for. Admin user left disabled (secure default — Container
   Apps will use a Managed Identity + `AcrPull` role in step 5, not a shared login). `az acr
   build --registry inspectiqacrshmuelstern --image inspectiq-backend:v1 backend/` — **the
   Dockerfile's first real build test, and it passed end-to-end** (ODBC Driver 18 install,
   `apt-mark manual libgssapi-krb5-2`, `pip install` including the new `azure-storage-blob`
   dependency). Hit the exact same `az acr build` tooling gotcha PropertyManager's session did:
   the local log-streaming crashes with a `UnicodeEncodeError` (Windows console `cp1252`
   choking on a Unicode character in the build log) that looks like a build failure but isn't —
   confirmed the real status via `az acr task list-runs` (polled until `Succeeded`, ~3 minutes)
   instead of trusting the crashed stream, then confirmed the image tag actually exists via
   `az acr repository show-tags`.
4. ~~Provision the storage account + container~~ — **done, 2026-08-26**: `inspectiqstorage`
   was already taken globally too — used `inspectiqstorageshm` instead. Standard_LRS,
   `AllowBlobPublicAccess: False` at the account level (an extra layer beyond the container's
   own `--public-access off`, confirmed in the account's own properties after creation) —
   `media` container created private, connection string saved to a local scratch file.
5. ~~Provision Container Apps environment + the backend app itself~~ — **done, 2026-08-26**:
   `inspectiq-env`, then `inspectiq-api` created with `--registry-identity system`
   (auto-provisions the system-assigned Managed Identity + `AcrPull` role in one step, no
   separate manual role-assignment command needed - simpler than PropertyManager's own session
   had available at the time). Every secret (`db-password`, `jwt-secret-key` — fresh via
   `secrets.token_urlsafe(64)`, `storage-connstr`) and env var from §3 wired in at create time.
   `--min-replicas 0 --max-replicas 2`. **Worked end-to-end on the very first deployment
   attempt** — `GET /api/health` returned `{"status":"ok","database":"connected"}` over real
   HTTPS against the real Azure SQL database, no `msodbcsql17` TLS hang, no
   `libgssapi-krb5-2` removal, no missing `Encrypt=yes` - all three of PropertyManager's
   hard-won bugs were pre-empted by building the fixes in from the start rather than
   rediscovering them live. Also explicitly configured liveness + readiness probes against
   `/api/health` (`az containerapp update --yaml` with a minimal template patch) — closing the
   exact gap PropertyManager's own Prompt 33 audit found and never got around to fixing
   (`probes: null` there, confirmed live). Verified the update didn't break anything: probes
   confirmed present via `az containerapp show`, health check still returns 200 immediately
   after.
6. Provision Static Web Apps + deploy the frontend (§5) — free tier.
7. Wire CORS back to the real frontend URL (§6).
8. Create the real Administrator account (§16).
9. Full post-deployment checklist (§16), live through the browser.
