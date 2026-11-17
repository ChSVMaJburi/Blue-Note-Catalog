from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.db import make_engine


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

    @application.get("/health/live", tags=["health"])
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", tags=["health"])
    def readiness(request: Request) -> dict[str, str]:
        try:
            with request.app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            raise HTTPException(503, "Database unavailable") from None
        return {"status": "ok"}

    return application
