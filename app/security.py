from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.config import Settings
from app.errors import unauthorized

ALGORITHM = "HS256"
ISSUER = "blue-note-catalog"
AUDIENCE = "blue-note-api"
MAX_ID = 2_147_483_647
password_hasher = PasswordHash.recommended()
dummy_password_hash = password_hasher.hash("not-an-account-password")


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
