from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import constraint_name
from app.models import Artist
from app.repositories import subscriptions
from app.repositories.catalog import paginate
from app.schemas.catalog import Pagination
from app.services.catalog import CatalogPage, not_found, page


def list_followed(session: Session, user_id: int, paging: Pagination) -> CatalogPage[Artist]:
    query = subscriptions.followed(user_id)
    return page(paginate(session, query, paging.limit, paging.offset), paging)


def follow(session: Session, user_id: int, artist_id: int) -> None:
    try:
        subscriptions.follow(session, user_id, artist_id)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if constraint_name(error) == "fk_subscriptions_artist_id_artists":
            raise not_found("artist") from None
        raise


def unfollow(session: Session, user_id: int, artist_id: int) -> None:
    subscriptions.unfollow(session, user_id, artist_id)
    session.commit()
