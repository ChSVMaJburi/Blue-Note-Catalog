import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ValidationIssue(BaseModel):
    location: list[str | int]
    code: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[ValidationIssue] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(Exception):
    def __init__(
        self, status: int, code: str, message: str, *, headers: Mapping[str, str] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers


def unauthorized(message: str = "A valid bearer token is required") -> AppError:
    return AppError(401, "unauthorized", message, headers={"WWW-Authenticate": "Bearer"})


def error_docs(*statuses: int) -> dict[int | str, dict[str, object]]:
    return {status: {"model": ErrorResponse} for status in statuses}


def error_response(
    status: int,
    code: str,
    message: str,
    *,
    headers: Mapping[str, str] | None = None,
    details: list[ValidationIssue] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details or []))
    return JSONResponse(
        status_code=status, content=payload.model_dump(mode="json"), headers=headers
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_request: Request, error: AppError) -> JSONResponse:
        return error_response(error.status, error.code, error.message, headers=error.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            ValidationIssue(location=list(issue["loc"]), code=issue["type"], message=issue["msg"])
            for issue in error.errors()
        ]
        return error_response(422, "validation_error", "Request validation failed", details=details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        code = {404: "route_not_found", 405: "method_not_allowed"}.get(
            error.status_code, "http_error"
        )
        return error_response(error.status_code, code, str(error.detail), headers=error.headers)

    @app.exception_handler(Exception)
    async def internal_error(_request: Request, error: Exception) -> JSONResponse:
        logger.error("Unhandled application error (%s)", type(error).__name__)
        return error_response(500, "internal_error", "Unexpected server error")
