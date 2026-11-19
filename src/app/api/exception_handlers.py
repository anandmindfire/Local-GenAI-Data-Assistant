"""Centralized FastAPI exception handlers ensuring sanitized, actionable error responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppBaseException
from app.core.logging import correlation_id_ctx

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers on the FastAPI application."""

    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
        correlation_id = correlation_id_ctx.get()
        logger.warning(
            f"AppException [{exc.category}]: {exc.message}",
            extra={
                "category": exc.category,
                "details": exc.details,
                "correlation_id": correlation_id,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.to_dict(),
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        correlation_id = correlation_id_ctx.get()
        errors = exc.errors()
        logger.warning(
            f"Request validation error: {errors}",
            extra={"details": errors, "correlation_id": correlation_id},
        )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "category": "VALIDATION_ERROR",
                    "message": "Invalid request parameters or payload.",
                    "details": [
                        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in errors
                    ],
                },
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = correlation_id_ctx.get()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "category": "HTTP_ERROR",
                    "message": str(exc.detail),
                    "details": {},
                },
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = correlation_id_ctx.get()
        logger.exception(
            f"Unhandled server exception: {exc}",
            extra={"correlation_id": correlation_id},
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "category": "INTERNAL_ERROR",
                    "message": (
                        "An unexpected internal server error occurred. Please try again later."
                    ),
                    "details": {},
                },
                "correlation_id": correlation_id,
            },
        )
