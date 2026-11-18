from functools import partial
from typing import Annotated

from fastapi import BackgroundTasks, Depends, Path, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import AppSettings, DbSession
from app.errors import unauthorized
from app.models import MAX_ID, User
from app.repositories import users
from app.security import read_access_token
from app.services.auth import require_admin_role
from app.services.notifications import notify_subscribers
from app.services.publication import TrackPublisher

ResourceId = Annotated[int, Path(gt=0, le=MAX_ID)]


def get_publisher(
    session: DbSession, background: BackgroundTasks, request: Request
) -> TrackPublisher:
    enqueue = partial(background.add_task, notify_subscribers, request.app.state.engine)
    return TrackPublisher(session, enqueue)


Publisher = Annotated[TrackPublisher, Depends(get_publisher)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False, bearerFormat="JWT"))
]


def get_current_user(token: BearerCredentials, settings: AppSettings, session: DbSession) -> User:
    if token is None:
        raise unauthorized()
    user = users.by_id(session, read_access_token(token.credentials, settings))
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    return require_admin_role(user)
