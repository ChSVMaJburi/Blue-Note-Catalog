import os
from collections.abc import Iterator
from pathlib import Path
from secrets import token_urlsafe

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.config import Settings
from app.db import make_engine
from app.main import create_app
from app.models import Role
from app.provision import API_ROLE, provision_role
from app.schemas.auth import Registration
from app.services.auth import create_account


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    host = os.environ.get("TEST_POSTGRES_HOST")
    if not host:
        pytest.skip("Use compose.test.yaml for PostgreSQL integration tests")
    return Settings(
        _env_file=None,
        postgres_host=host,
        postgres_port=5432,
        postgres_db="music_catalog_test",
        postgres_user="postgres",
        postgres_password=token_urlsafe(),
        jwt_secret=token_urlsafe(48),
    )


@pytest.fixture(scope="session")
def migration_config(test_settings: Settings) -> Config:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.attributes.update(database_settings=test_settings, configure_logger=False)
    return config


@pytest.fixture(scope="session")
def engine(test_settings: Settings, migration_config: Config) -> Iterator[Engine]:
    command.upgrade(migration_config, "head")
    provision_role(test_settings, test_settings.postgres_password.get_secret_value())
    database = make_engine(test_settings)
    try:
        yield database
    finally:
        database.dispose()


@pytest.fixture
def database(engine: Engine) -> Engine:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE playlist_tracks, playlists, subscriptions, tracks, albums, "
                "artists, users RESTART IDENTITY"
            )
        )
    return engine


@pytest.fixture
def client(database: Engine, test_settings: Settings) -> Iterator[TestClient]:
    with TestClient(
        create_app(test_settings.model_copy(update={"postgres_user": API_ROLE}))
    ) as http:
        yield http


@pytest.fixture
def make_user(client: TestClient):
    def register_and_login(username: str = "listener") -> dict[str, str]:
        password = token_urlsafe()
        credentials = {"username": username, "password": password}
        result = client.post(
            "/api/v1/auth/register",
            json={**credentials, "email": f"{username}@example.com"},
        )
        assert result.status_code == 201, result.text
        login = client.post("/api/v1/auth/login", json=credentials)
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    return register_and_login


@pytest.fixture
def admin_headers(client: TestClient, database: Engine) -> dict[str, str]:
    password = token_urlsafe()
    with Session(database, expire_on_commit=False) as session:
        create_account(
            session,
            Registration(username="operator", email="operator@example.com", password=password),
            role=Role.ADMIN,
        )
    login = client.post("/api/v1/auth/login", json={"username": "operator", "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
