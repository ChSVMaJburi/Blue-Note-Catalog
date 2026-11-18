from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.dependencies import CurrentUser, ResourceId
from app.db import DbSession
from app.errors import error_docs
from app.schemas.catalog import ArtistRead, Page, Pagination
from app.services import subscriptions

router = APIRouter(
    prefix="/me/subscriptions", tags=["subscriptions"], responses=error_docs(401, 422)
)


@router.get("", response_model=Page[ArtistRead])
def list_subscriptions(
    paging: Annotated[Pagination, Query()], user: CurrentUser, session: DbSession
):
    return subscriptions.list_followed(session, user.id, paging)


@router.put("/{artist_id}", status_code=204, responses=error_docs(404))
def follow_artist(artist_id: ResourceId, user: CurrentUser, session: DbSession) -> Response:
    subscriptions.follow(session, user.id, artist_id)
    return Response(status_code=204)


@router.delete("/{artist_id}", status_code=204)
def unfollow_artist(artist_id: ResourceId, user: CurrentUser, session: DbSession) -> Response:
    subscriptions.unfollow(session, user.id, artist_id)
    return Response(status_code=204)
