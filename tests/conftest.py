from secrets import token_urlsafe

import pytest

from app.config import Settings


@pytest.fixture
def token_settings() -> Settings:
    return Settings(_env_file=None, postgres_password=token_urlsafe(), jwt_secret=token_urlsafe(48))
