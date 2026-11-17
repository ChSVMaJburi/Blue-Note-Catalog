from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import constraint_name
from app.errors import AppError, unauthorized
from app.models import Role, User
from app.repositories import users
from app.schemas.auth import LoginRequest, Registration
from app.security import dummy_password_hash, password_hasher


def create_account(session: Session, data: Registration, *, role: Role = Role.USER) -> User:
    user = User(
        username=data.username,
        email=data.email,
        password_hash=password_hasher.hash(data.password.get_secret_value()),
        role=role,
    )
    users.add(session, user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if constraint_name(error) in {"uq_users_username", "uq_users_email"}:
            raise AppError(
                409, "account_exists", "An account with this username or email already exists"
            ) from None
        raise
    return user


def authenticate(session: Session, data: LoginRequest) -> User:
    user = users.by_username(session, data.username)
    stored_hash = user.password_hash if user else dummy_password_hash
    verified = password_hasher.verify(data.password.get_secret_value(), stored_hash)
    if not verified or user is None:
        raise unauthorized("Invalid username or password")
    return user


def require_admin_role(user: User) -> User:
    if user.role != Role.ADMIN:
        raise AppError(403, "forbidden", "Administrator access is required")
    return user
