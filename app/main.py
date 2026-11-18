from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.playlists import router as playlists_router
from app.config import Settings
from app.db import make_engine
from app.errors import AppError, error_docs, install_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.settings = settings or Settings()
        application.state.engine = make_engine(application.state.settings)
        try:
            yield
        finally:
            application.state.engine.dispose()

    application = FastAPI(
        title="Blue Note Catalog",
        description="REST API for a jazz music catalog.",
        version="0.1.0",
        lifespan=lifespan,
    )
    install_error_handlers(application)
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(catalog_router, prefix="/api/v1")
    application.include_router(playlists_router, prefix="/api/v1")

    @application.get("/health/live", tags=["health"])
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", tags=["health"], responses=error_docs(503))
    def readiness(request: Request) -> dict[str, str]:
        try:
            with request.app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            raise AppError(503, "database_unavailable", "Database unavailable") from None
        return {"status": "ok"}

    return application
