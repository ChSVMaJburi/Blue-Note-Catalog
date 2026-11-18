from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Album, Artist, Subscription, Track, User


def followed(user_id: int):
    return (
        select(Artist).join(Subscription).where(Subscription.user_id == user_id).order_by(Artist.id)
    )


def follow(session: Session, user_id: int, artist_id: int) -> None:
    session.execute(
        insert(Subscription).values(user_id=user_id, artist_id=artist_id).on_conflict_do_nothing()
    )


def unfollow(session: Session, user_id: int, artist_id: int) -> None:
    session.execute(
        delete(Subscription).where(
            Subscription.user_id == user_id, Subscription.artist_id == artist_id
        )
    )


def track_details(session: Session, track_ids: list[int]):
    return session.execute(
        select(Track.id, Track.title, Artist.id.label("artist_id"), Artist.name)
        .select_from(Track)
        .join(Album)
        .join(Artist)
        .where(Track.id.in_(track_ids))
        .order_by(Artist.id, Track.id)
    ).all()


def recipients(session: Session, artist_id: int, after: int, limit: int):
    return session.execute(
        select(User.id, User.email)
        .join(Subscription)
        .where(Subscription.artist_id == artist_id, User.id > after)
        .order_by(User.id)
        .limit(limit)
    ).all()
