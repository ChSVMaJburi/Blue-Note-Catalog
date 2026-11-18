from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.dependencies import CurrentUser, ResourceId
from app.db import DbSession
from app.errors import error_docs
from app.schemas.catalog import Page, Pagination, TrackRead
from app.schemas.playlists import PlaylistInput, PlaylistRead
from app.services import playlists

router = APIRouter(prefix="/me/playlists", tags=["playlists"], responses=error_docs(401, 404, 422))


@router.post("", status_code=201, response_model=PlaylistRead)
def create_playlist(data: PlaylistInput, user: CurrentUser, session: DbSession):
    return playlists.create(session, user.id, data.name)


@router.get("", response_model=Page[PlaylistRead])
def list_playlists(paging: Annotated[Pagination, Query()], user: CurrentUser, session: DbSession):
    return playlists.list_owned(session, user.id, paging)


@router.get("/{playlist_id}", response_model=PlaylistRead)
def get_playlist(playlist_id: ResourceId, user: CurrentUser, session: DbSession):
    return playlists.get(session, user.id, playlist_id)


@router.patch("/{playlist_id}", response_model=PlaylistRead)
def rename_playlist(
    playlist_id: ResourceId, data: PlaylistInput, user: CurrentUser, session: DbSession
):
    return playlists.rename(session, user.id, playlist_id, data.name)


@router.delete("/{playlist_id}", status_code=204)
def delete_playlist(playlist_id: ResourceId, user: CurrentUser, session: DbSession) -> Response:
    playlists.remove(session, user.id, playlist_id)
    return Response(status_code=204)


@router.get("/{playlist_id}/tracks", response_model=Page[TrackRead])
def playlist_tracks(
    playlist_id: ResourceId,
    paging: Annotated[Pagination, Query()],
    user: CurrentUser,
    session: DbSession,
):
    return playlists.list_tracks(session, user.id, playlist_id, paging)


@router.put("/{playlist_id}/tracks/{track_id}", status_code=204)
def add_track(
    playlist_id: ResourceId, track_id: ResourceId, user: CurrentUser, session: DbSession
) -> Response:
    playlists.add_track(session, user.id, playlist_id, track_id)
    return Response(status_code=204)


@router.delete("/{playlist_id}/tracks/{track_id}", status_code=204)
def remove_track(
    playlist_id: ResourceId, track_id: ResourceId, user: CurrentUser, session: DbSession
) -> Response:
    playlists.remove_track(session, user.id, playlist_id, track_id)
    return Response(status_code=204)
