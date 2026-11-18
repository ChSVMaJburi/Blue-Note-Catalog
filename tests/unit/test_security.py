from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

import jwt
import pytest

from app.config import Settings
from app.errors import AppError
from app.models import Role, User
from app.security import ALGORITHM, AUDIENCE, ISSUER, issue_access_token, read_access_token
from app.services.auth import require_admin_role


def test_jwt_round_trip(token_settings: Settings) -> None:
    assert read_access_token(issue_access_token(42, token_settings), token_settings) == 42


@pytest.mark.parametrize(
    "scenario", ["expired", "issuer", "audience", "subject", "signature", "exp"]
)
def test_invalid_jwt_is_unauthorized(token_settings: Settings, scenario: str) -> None:
    now = datetime.now(UTC)
    claims = {
        "sub": "42",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now - timedelta(minutes=2),
        "exp": now + timedelta(minutes=2),
    }
    secret = token_settings.jwt_secret.get_secret_value()
    if scenario == "expired":
        claims["exp"] = now - timedelta(minutes=1)
    elif scenario == "issuer":
        claims["iss"] = "another-issuer"
    elif scenario == "audience":
        claims["aud"] = "another-api"
    elif scenario == "subject":
        claims["sub"] = "2147483648"
    elif scenario == "signature":
        secret = token_urlsafe(48)
    elif scenario == "exp":
        del claims["exp"]

    with pytest.raises(AppError) as caught:
        read_access_token(jwt.encode(claims, secret, algorithm=ALGORITHM), token_settings)
    assert caught.value.status == 401
    assert caught.value.headers == {"WWW-Authenticate": "Bearer"}


def test_admin_role_required() -> None:
    user = User(role=Role.USER)
    with pytest.raises(AppError) as caught:
        require_admin_role(user)
    assert caught.value.status == 403
    admin = User(role=Role.ADMIN)
    assert require_admin_role(admin) is admin
