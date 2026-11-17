from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.db import constraint_name
from app.errors import AppError
from app.models import Album, Artist, Base, Track
from app.repositories import catalog
from app.schemas.catalog import AlbumFilters, ArtistFilters, TrackFilters

PARENT_CONSTRAINTS = {"fk_albums_artist_id_artists": "artist", "fk_tracks_album_id_albums": "album"}
UNIQUENESS_ERRORS = {
    "uq_albums_artist_title": (
        "album_title_conflict",
        "This artist already has an album with this title",
    ),
    "uq_tracks_album_number": (
        "track_number_conflict",
        "This number is already used on this album",
    ),
}


def not_found(resource: str) -> AppError:
    return AppError(404, f"{resource}_not_found", f"{resource.capitalize()} not found")


class CatalogService[Entity: Base]:
    def __init__(self, model: type[Entity], label: str) -> None:
        self.model = model
        self.label = label

    def get(self, session: Session, entity_id: int) -> Entity:
        entity = catalog.get(session, self.model, entity_id)
        if entity is None:
            raise not_found(self.label)
        return entity

    def create(self, session: Session, attributes: Mapping[str, object]) -> Entity:
        entity = self.model(**attributes)
        catalog.add(session, entity)
        self._commit(session)
        return entity

    def update(self, session: Session, entity_id: int, changes: Mapping[str, object]) -> Entity:
        entity = self.get(session, entity_id)
        for name, value in changes.items():
            setattr(entity, name, value)
        self._commit(session)
        return entity

    def delete(self, session: Session, entity_id: int) -> None:
        catalog.remove(session, self.get(session, entity_id))
        self._commit(session, deleting=True)

    def _commit(self, session: Session, *, deleting: bool = False) -> None:
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            constraint = constraint_name(error)
            if constraint in UNIQUENESS_ERRORS:
                code, message = UNIQUENESS_ERRORS[constraint]
                raise AppError(409, code, message) from None
            if constraint in PARENT_CONSTRAINTS:
                if deleting:
                    raise AppError(
                        409, "resource_in_use", "Remove dependent catalog entries first"
                    ) from None
                raise not_found(PARENT_CONSTRAINTS[constraint]) from None
            raise
        except StaleDataError:
            session.rollback()
            raise not_found(self.label) from None


artists = CatalogService(Artist, "artist")
albums = CatalogService(Album, "album")
tracks = CatalogService(Track, "track")


@dataclass(frozen=True, slots=True)
class CatalogPage[Entity]:
    items: Sequence[Entity]
    limit: int
    offset: int
    has_more: bool


def page[Entity](items: Sequence[Entity], filters: ArtistFilters) -> CatalogPage[Entity]:
    return CatalogPage(
        items=items[: filters.limit],
        limit=filters.limit,
        offset=filters.offset,
        has_more=len(items) > filters.limit,
    )


def list_artists(session: Session, filters: ArtistFilters) -> CatalogPage[Artist]:
    return page(
        catalog.find_artists(session, q=filters.q, limit=filters.limit, offset=filters.offset),
        filters,
    )


def list_albums(session: Session, filters: AlbumFilters) -> CatalogPage[Album]:
    return page(
        catalog.find_albums(
            session,
            artist_id=filters.artist_id,
            q=filters.q,
            limit=filters.limit,
            offset=filters.offset,
        ),
        filters,
    )


def list_tracks(session: Session, filters: TrackFilters) -> CatalogPage[Track]:
    return page(
        catalog.find_tracks(
            session,
            artist_id=filters.artist_id,
            album_id=filters.album_id,
            q=filters.q,
            limit=filters.limit,
            offset=filters.offset,
        ),
        filters,
    )
