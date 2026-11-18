from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Playlist, PlaylistTrack, Track


def owned(session: Session, owner_id: int, playlist_id: int, *, lock: bool) -> Playlist | None:
    query = select(Playlist).where(Playlist.id == playlist_id, Playlist.owner_id == owner_id)
    return session.scalar(query.with_for_update() if lock else query)


def by_owner(owner_id: int):
    return select(Playlist).where(Playlist.owner_id == owner_id).order_by(Playlist.id)


def contents(playlist_id: int):
    return (
        select(Track)
        .join(PlaylistTrack)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.added_at, Track.id)
    )


def add_track(session: Session, playlist_id: int, track_id: int) -> None:
    session.execute(
        insert(PlaylistTrack)
        .values(playlist_id=playlist_id, track_id=track_id)
        .on_conflict_do_nothing()
    )


def remove_track(session: Session, playlist_id: int, track_id: int) -> None:
    session.execute(
        delete(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == track_id
        )
    )
