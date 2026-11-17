from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Album, Artist, Base, Track


def get[Entity: Base](session: Session, model: type[Entity], entity_id: int) -> Entity | None:
    return session.get(model, entity_id)


def add(session: Session, entity: Base) -> None:
    session.add(entity)


def remove(session: Session, entity: Base) -> None:
    session.delete(entity)


def paginate[Entity](
    session: Session, query: Select[tuple[Entity]], limit: int, offset: int
) -> Sequence[Entity]:
    return session.scalars(query.offset(offset).limit(limit + 1)).all()


def find_artists(session: Session, *, q: str | None, limit: int, offset: int) -> Sequence[Artist]:
    query = select(Artist).order_by(Artist.id)
    if q is not None:
        query = query.where(Artist.name.icontains(q, autoescape=True))
    return paginate(session, query, limit, offset)


def find_albums(
    session: Session, *, artist_id: int | None, q: str | None, limit: int, offset: int
) -> Sequence[Album]:
    query = select(Album).order_by(Album.id)
    if artist_id is not None:
        query = query.where(Album.artist_id == artist_id)
    if q is not None:
        query = query.where(Album.title.icontains(q, autoescape=True))
    return paginate(session, query, limit, offset)


def find_tracks(
    session: Session,
    *,
    artist_id: int | None,
    album_id: int | None,
    q: str | None,
    limit: int,
    offset: int,
) -> Sequence[Track]:
    query = select(Track).order_by(Track.id)
    if artist_id is not None:
        query = query.join(Album, Album.id == Track.album_id).where(Album.artist_id == artist_id)
    if album_id is not None:
        query = query.where(Track.album_id == album_id)
    if q is not None:
        query = query.where(Track.title.icontains(q, autoescape=True))
    return paginate(session, query, limit, offset)
