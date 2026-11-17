from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models import User


def by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def credentials_by_username(session: Session, username: str) -> Row[tuple[int, str]] | None:
    return session.execute(
        select(User.id, User.password_hash).where(User.username == username)
    ).one_or_none()


def add(session: Session, user: User) -> None:
    session.add(user)
