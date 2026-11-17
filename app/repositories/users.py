from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def add(session: Session, user: User) -> None:
    session.add(user)
