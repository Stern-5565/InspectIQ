import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api import auth, health, inspection_templates, inspections, maintenance, media, properties, units
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging

configure_logging(settings.APP_DEBUG)
logger = logging.getLogger("inspectiq")

app = FastAPI(title="InspectIQ API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Logged with full detail server-side; the client only ever sees a generic message -
    # never leak internals in error responses (PROJECT_PLAN.md §12).
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(properties.router, prefix="/api")
app.include_router(units.router, prefix="/api")
app.include_router(inspection_templates.router, prefix="/api")
app.include_router(inspections.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(maintenance.router, prefix="/api")
