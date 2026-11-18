from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import constraint_name
from app.models import Playlist, Track
from app.repositories import playlists
from app.repositories.catalog import paginate
from app.schemas.catalog import Pagination
from app.services.catalog import CatalogPage, not_found, page


def get(session: Session, owner: int, playlist_id: int, *, lock: bool = False) -> Playlist:
    playlist = playlists.owned(session, owner, playlist_id, lock=lock)
    if playlist is None:
        raise not_found("playlist")
    return playlist


def create(session: Session, owner: int, name: str) -> Playlist:
    playlist = Playlist(owner_id=owner, name=name)
    session.add(playlist)
    session.commit()
    return playlist


def rename(session: Session, owner: int, playlist_id: int, name: str) -> Playlist:
    playlist = get(session, owner, playlist_id, lock=True)
    playlist.name = name
    session.commit()
    return playlist


def remove(session: Session, owner: int, playlist_id: int) -> None:
    session.delete(get(session, owner, playlist_id, lock=True))
    session.commit()


def list_owned(session: Session, owner: int, paging: Pagination) -> CatalogPage[Playlist]:
    return page(paginate(session, playlists.by_owner(owner), paging.limit, paging.offset), paging)


def list_tracks(
    session: Session, owner: int, playlist_id: int, paging: Pagination
) -> CatalogPage[Track]:
    get(session, owner, playlist_id)
    return page(
        paginate(session, playlists.contents(playlist_id), paging.limit, paging.offset), paging
    )


def add_track(session: Session, owner: int, playlist_id: int, track_id: int) -> None:
    get(session, owner, playlist_id, lock=True)
    try:
        playlists.add_track(session, playlist_id, track_id)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if constraint_name(error) == "fk_playlist_tracks_track_id_tracks":
            raise not_found("track") from None
        raise


def remove_track(session: Session, owner: int, playlist_id: int, track_id: int) -> None:
    get(session, owner, playlist_id, lock=True)
    playlists.remove_track(session, playlist_id, track_id)
    session.commit()
