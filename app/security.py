from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import BoundedSemaphore

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.config import Settings
from app.errors import AppError, unauthorized
from app.models import MAX_ID

ALGORITHM = "HS256"
ISSUER = "blue-note-catalog"
AUDIENCE = "blue-note-api"
password_hasher = PasswordHash.recommended()
dummy_password_hash = password_hasher.hash("not-an-account-password")
password_slots = BoundedSemaphore(4)


@contextmanager
def password_capacity() -> Iterator[None]:
    if not password_slots.acquire(blocking=False):
        raise AppError(
            503, "auth_busy", "Password verification capacity is busy", headers={"Retry-After": "1"}
        )
    try:
        yield
    finally:
        password_slots.release()


def issue_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm=ALGORITHM,
    )


def read_access_token(token: str, settings: Settings) -> int:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["sub", "iss", "aud", "iat", "exp"]},
        )
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
            raise ValueError("Invalid subject")
        if not 1 <= len(subject) <= 10 or not 1 <= int(subject) <= MAX_ID:
            raise ValueError("Invalid subject")
        return int(subject)
    except (InvalidTokenError, TypeError, ValueError):
        raise unauthorized() from None
