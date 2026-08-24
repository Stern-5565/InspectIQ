# InspectIQ Frontend

React + React Router + Axios, mobile-first. See
[`../docs/PROJECT_PLAN.md §6-7`](../docs/PROJECT_PLAN.md) for the architecture this follows.

## Prerequisites

- Node.js 20+ (built against Node 24)
- The backend running locally (see [`../backend/README.md`](../backend/README.md)) - this app has
  no mock API layer, every page hits the real FastAPI backend

## Setup

```bash
npm install
copy .env.example .env       # then edit VITE_API_BASE_URL/VITE_API_ORIGIN if your backend isn't on localhost:8000
```

## Run locally

```bash
npm run dev
```

Then visit `http://localhost:5173`. Log in with one of the demo accounts seeded by
`backend/scripts/seed_demo_users.py` (e.g. `admin@northgatepm.example` / `Password123!`).

## Layout

```
src/
    api/            Shared Axios instance - token handling, refresh-and-retry (client.js)
    services/       One file per backend resource, wraps api/client.js - no component calls
                     Axios directly
    contexts/       AuthContext (current user, token, login/logout)
    routes/         ProtectedRoute - auth-gated, optionally role-gated route trees
    components/     Reusable, cross-page (LoadingSpinner, ErrorBoundary, ... - grows per module)
    layouts/        MainLayout/Header/Sidebar - the authenticated app shell
    pages/          One folder per module, built incrementally alongside each backend module's
                     frontend (only auth/dashboard exist so far - see docs/AI_HANDOFF.md)
    constants/      roles.js - mirrors backend/app/security/roles.py
    utilities/      apiError.js (error-message extraction), permissions.js (role checks)
```

Built module-by-module, same order as the backend, not all 19 scope-listed pages at once - see
`docs/AI_HANDOFF.md` for what's built so far and what's next.
