from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import constraint_name
from app.errors import AppError, unauthorized
from app.models import Role, User
from app.repositories import users
from app.schemas.auth import LoginRequest, Registration
from app.security import dummy_password_hash, password_capacity, password_hasher


def create_account(session: Session, data: Registration, *, role: Role = Role.USER) -> User:
    with password_capacity():
        hashed = password_hasher.hash(data.password.get_secret_value())
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hashed,
    )
    if role == Role.ADMIN:
        user.role = role
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


def authenticate(session: Session, data: LoginRequest) -> int:
    with session.begin():
        credentials = users.credentials_by_username(session, data.username)
    stored_hash = credentials.password_hash if credentials else dummy_password_hash
    with password_capacity():
        verified = password_hasher.verify(data.password.get_secret_value(), stored_hash)
    if not verified or credentials is None:
        raise unauthorized("Invalid username or password")
    return credentials.id


def require_admin_role(user: User) -> User:
    if user.role != Role.ADMIN:
        raise AppError(403, "forbidden", "Administrator access is required")
    return user
