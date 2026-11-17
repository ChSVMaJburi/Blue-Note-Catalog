from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import DatabaseSettings, Settings


def make_engine(settings: DatabaseSettings) -> Engine:
    return create_engine(
        settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3}
    )


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        yield session


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


DbSession = Annotated[Session, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]
