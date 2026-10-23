"""FastAPI application factory and unified JSON error envelope handlers."""

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditor.api.audits import router as audits_router
from auditor.api.schemas import HealthResponse
from auditor.api.webhooks import router as webhooks_router
from auditor.db.session import get_db


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="AI Code Auditor API",
        description="Automated Code Review and Bug Detection Service for Pull Requests",
        version="0.1.0",
    )

    # Health check endpoints
    @app.get("/health", response_model=HealthResponse, tags=["system"])
    @app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    def health_check(db: Session = Depends(get_db)) -> HealthResponse:  # noqa: B008
        """Verify server readiness and database connectivity."""
        try:
            db.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        return HealthResponse(status="healthy", database=db_status, version="0.1.0")

    # Register routers
    app.include_router(webhooks_router)
    app.include_router(audits_router)

    # Unified exception handler for HTTPExceptions adhering to canonical JSON Error Envelope
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            error_payload = {
                "error": {
                    "code": exc.detail.get("code", "ERROR"),
                    "message": exc.detail.get("message", "An error occurred."),
                    "details": exc.detail.get("details"),
                }
            }
        else:
            error_payload = {
                "error": {
                    "code": "HTTP_ERROR",
                    "message": str(exc.detail),
                    "details": None,
                }
            }
        return JSONResponse(status_code=exc.status_code, content=error_payload)

    # Unified exception handler for Pydantic/Request validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        error_payload = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request payload validation failed.",
                "details": exc.errors(),
            }
        }
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_payload)

    # Catch-all internal server error handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        error_payload = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": str(exc),
            }
        }
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_payload)

    return app
