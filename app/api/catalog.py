from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import ResourceId, require_admin
from app.db import DbSession
from app.errors import error_docs
from app.models import Album, Artist, Track
from app.schemas.catalog import (
    AlbumCreate,
    AlbumFilters,
    AlbumPatch,
    AlbumRead,
    ArtistCreate,
    ArtistFilters,
    ArtistPatch,
    ArtistRead,
    Page,
    TrackCreate,
    TrackFilters,
    TrackPatch,
    TrackRead,
)
from app.services import catalog
from app.services.catalog import CatalogPage

router = APIRouter(tags=["catalog"], responses=error_docs(422, 500))
admin_only = [Depends(require_admin)]


@router.get("/artists", response_model=Page[ArtistRead])
def list_artists(
    filters: Annotated[ArtistFilters, Query()], session: DbSession
) -> CatalogPage[Artist]:
    return catalog.list_artists(session, filters)


@router.post(
    "/artists",
    response_model=ArtistRead,
    status_code=201,
    dependencies=admin_only,
    responses=error_docs(401, 403),
)
def create_artist(data: ArtistCreate, session: DbSession) -> Artist:
    return catalog.artists.create(session, data.model_dump())


@router.get("/artists/{artist_id}", response_model=ArtistRead, responses=error_docs(404))
def get_artist(artist_id: ResourceId, session: DbSession) -> Artist:
    return catalog.artists.get(session, artist_id)


@router.patch(
    "/artists/{artist_id}",
    response_model=ArtistRead,
    dependencies=admin_only,
    responses=error_docs(401, 403, 404),
)
def update_artist(artist_id: ResourceId, data: ArtistPatch, session: DbSession) -> Artist:
    return catalog.artists.update(session, artist_id, data)


@router.delete(
    "/artists/{artist_id}",
    status_code=204,
    dependencies=admin_only,
    responses=error_docs(401, 403, 404, 409),
)
def delete_artist(artist_id: ResourceId, session: DbSession) -> Response:
    catalog.artists.delete(session, artist_id)
    return Response(status_code=204)


@router.get("/albums", response_model=Page[AlbumRead])
def list_albums(
    filters: Annotated[AlbumFilters, Query()], session: DbSession
) -> CatalogPage[Album]:
    return catalog.list_albums(session, filters)


@router.post(
    "/albums",
    response_model=AlbumRead,
    status_code=201,
    dependencies=admin_only,
    responses=error_docs(401, 403, 404, 409),
)
def create_album(data: AlbumCreate, session: DbSession) -> Album:
    return catalog.albums.create(session, data.model_dump())


@router.get("/albums/{album_id}", response_model=AlbumRead, responses=error_docs(404))
def get_album(album_id: ResourceId, session: DbSession) -> Album:
    return catalog.albums.get(session, album_id)


@router.patch(
    "/albums/{album_id}",
    response_model=AlbumRead,
    dependencies=admin_only,
    responses=error_docs(401, 403, 404, 409),
)
def update_album(album_id: ResourceId, data: AlbumPatch, session: DbSession) -> Album:
    return catalog.albums.update(session, album_id, data)


@router.delete(
    "/albums/{album_id}",
    status_code=204,
    dependencies=admin_only,
    responses=error_docs(401, 403, 404, 409),
)
def delete_album(album_id: ResourceId, session: DbSession) -> Response:
    catalog.albums.delete(session, album_id)
    return Response(status_code=204)


@router.get("/tracks", response_model=Page[TrackRead])
def list_tracks(
    filters: Annotated[TrackFilters, Query()], session: DbSession
) -> CatalogPage[Track]:
    return catalog.list_tracks(session, filters)


@router.post(
    "/tracks",
    response_model=TrackRead,
    status_code=201,
    dependencies=admin_only,
    responses=error_docs(401, 403, 404, 409),
)
def create_track(data: TrackCreate, session: DbSession) -> Track:
    return catalog.tracks.create(session, data.model_dump())


@router.get("/tracks/{track_id}", response_model=TrackRead, responses=error_docs(404))
def get_track(track_id: ResourceId, session: DbSession) -> Track:
    return catalog.tracks.get(session, track_id)


@router.patch(
    "/tracks/{track_id}",
    response_model=TrackRead,
    dependencies=admin_only,
    responses=error_docs(401, 403, 404, 409),
)
def update_track(track_id: ResourceId, data: TrackPatch, session: DbSession) -> Track:
    return catalog.tracks.update(session, track_id, data)


@router.delete(
    "/tracks/{track_id}",
    status_code=204,
    dependencies=admin_only,
    responses=error_docs(401, 403, 404),
)
def delete_track(track_id: ResourceId, session: DbSession) -> Response:
    catalog.tracks.delete(session, track_id)
    return Response(status_code=204)
