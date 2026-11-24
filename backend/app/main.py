"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import ApiError, api_error_handler
from app.database.session import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # In development with SQLite, create tables automatically so local verification works
    # without a migration tool. Production uses Alembic migrations exclusively.
    if settings.is_sqlite:
        import app.models  # noqa: F401 - register mappers
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Role-based backend for examination registration, internal marks, result processing, "
        "SGPA/CGPA, recounting, notifications and document generation. "
        "Exactly three roles: STUDENT, FACULTY, EXAM_ADMIN."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(p) for p in error["loc"][1:]), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Validation failed", "errors": errors, "code": "validation_error"},
    )


@app.get("/health", tags=["System"])
def health() -> dict:
    return {"status": "ok", "service": "smart-exam-system", "environment": settings.environment}


app.include_router(api_router, prefix=settings.api_prefix)
