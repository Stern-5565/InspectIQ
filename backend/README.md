# InspectIQ Backend

FastAPI + SQLAlchemy + SQL Server. See [`../docs/PROJECT_PLAN.md`](../docs/PROJECT_PLAN.md) for
the architecture and [`../docs/DATABASE.md`](../docs/DATABASE.md) for the schema this connects to.

## Prerequisites

- Python 3.14+
- A running SQL Server instance with the `InspectIQDb` schema applied (see
  [`../database/scripts/00_RunAll.sql`](../database/scripts/00_RunAll.sql))
- ODBC Driver 17 (or 18) for SQL Server installed

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements-dev.txt
copy .env.example .env       # then edit DB_SERVER etc. for your environment
```

## Run locally

```bash
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/api/health` (should return
`{"status": "ok", "database": "connected"}`) or `http://127.0.0.1:8000/docs` for the
auto-generated Swagger UI.

## Run tests

```bash
pytest
```

Tests hit a real database (no mocks — see [`../docs/AI_MEMORY.md`](../docs/AI_MEMORY.md) for why)
via the same `.env` config the app itself uses, so a working `InspectIQDb` connection is required
before `pytest` will pass.

## Layout

```
app/
    api/            FastAPI routers - thin, no business logic
    core/           config, logging, domain exceptions
    database/       SQLAlchemy engine/session
    models/         SQLAlchemy ORM models (one file per table group, added as each module is built)
    schemas/        Pydantic request/response models
    repositories/   DB access only, no business rules
    services/       business logic - the only layer allowed to enforce rules
    security/       password hashing, JWT, auth dependencies (Phase 5)
    main.py         app factory, middleware, exception handlers, router registration
tests/
```
