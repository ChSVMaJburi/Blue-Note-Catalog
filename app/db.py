from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from psycopg import Error as PsycopgError
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import DatabaseSettings, Settings


def make_engine(settings: DatabaseSettings) -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )


def constraint_name(error: IntegrityError) -> str | None:
    return error.orig.diag.constraint_name if isinstance(error.orig, PsycopgError) else None


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        yield session


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


DbSession = Annotated[Session, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]
