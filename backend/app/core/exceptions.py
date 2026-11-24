"""Domain exceptions and a single error handler that produces the API error envelope."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        errors: list[Any] | None = None,
        code: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.errors = errors or []
        self.code = code
        super().__init__(message)


class ForbiddenError(ApiError):
    def __init__(self, message: str = "You do not have permission to perform this action") -> None:
        super().__init__(403, message, code="forbidden")


class PasswordChangeRequiredError(ApiError):
    def __init__(self, message: str = "You must change your temporary password before continuing") -> None:
        super().__init__(403, message, code="password_change_required")


class NotFoundError(ApiError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(404, message, code="not_found")


class ConflictError(ApiError):
    def __init__(self, message: str = "The request conflicts with existing data") -> None:
        super().__init__(409, message, code="conflict")


class ValidationError(ApiError):
    def __init__(self, message: str = "Validation failed", errors: list[Any] | None = None) -> None:
        super().__init__(422, message, errors, code="validation_error")


class UnauthorizedError(ApiError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(401, message, code="unauthorized")


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    body: dict[str, Any] = {"success": False, "message": exc.message}
    if exc.code:
        body["code"] = exc.code
    if exc.errors:
        body["errors"] = exc.errors
    return JSONResponse(status_code=exc.status_code, content=body)
