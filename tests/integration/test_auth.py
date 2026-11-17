from contextlib import ExitStack
from secrets import token_urlsafe

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Role, User
from app.schemas.auth import LoginRequest
from app.security import password_capacity, password_hasher
from app.services.auth import authenticate

pytestmark = pytest.mark.integration


def test_auth_overload_is_retryable(client: TestClient) -> None:
    credentials = {"username": "listener", "password": token_urlsafe()}
    account = {**credentials, "email": "listener@example.com"}
    with ExitStack() as occupied:
        for _ in range(4):
            occupied.enter_context(password_capacity())
        for route, data in [("login", credentials), ("register", account)]:
            busy = client.post(f"/api/v1/auth/{route}", json=data)
            assert busy.status_code == 503
            assert busy.headers["Retry-After"] == "1"
            assert busy.json()["error"]["code"] == "auth_busy"
    assert client.post("/api/v1/auth/register", json=account).status_code == 201


def test_login_releases_connection_before_argon2(client, database, monkeypatch) -> None:
    password = token_urlsafe()
    credentials = {"username": "listener", "password": password}
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                **credentials,
                "email": "listener@example.com",
            },
        ).status_code
        == 201
    )
    verify = password_hasher.verify
    with Session(database) as session:

        def checked_verify(plain, hashed):
            assert not session.in_transaction()
            return verify(plain, hashed)

        monkeypatch.setattr(password_hasher, "verify", checked_verify)
        assert authenticate(session, LoginRequest(**credentials)) > 0


def test_register_login_and_read_profile(client: TestClient, database: Engine) -> None:
    password = token_urlsafe()
    registration = {"username": "Jazz_Fan", "email": "Fan@Example.com", "password": password}
    created = client.post("/api/v1/auth/register", json=registration)
    assert created.status_code == 201, created.text
    profile = created.json()
    assert {"id", "username", "email", "role", "created_at"} == profile.keys()
    assert profile["username"] == "jazz_fan"
    assert profile["email"] == "fan@example.com"
    assert profile["role"] == "user"

    with Session(database) as session:
        user = session.scalar(select(User).where(User.id == profile["id"]))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert user.password_hash != password
        assert password_hasher.verify(password, user.password_hash)

    login = client.post("/api/v1/auth/login", json={"username": "JAZZ_FAN", "password": password})
    assert login.status_code == 200, login.text
    assert login.headers["Cache-Control"] == "no-store"
    assert login.json()["token_type"] == "bearer"

    auth = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = client.get("/api/v1/auth/me", headers=auth)
    assert me.json() == profile
    assert me.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("field", ["username", "email"])
def test_duplicate_registration_rolls_back(client: TestClient, field: str) -> None:
    password = token_urlsafe()
    initial = {"username": "listener", "email": "fan@example.com", "password": password}
    duplicate = {"username": "other_fan", "email": "other@example.com", "password": password}
    duplicate[field] = initial[field].upper()
    assert client.post("/api/v1/auth/register", json=initial).status_code == 201
    rejected = client.post("/api/v1/auth/register", json=duplicate)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "account_exists"
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"username": "other_fan", "email": "other@example.com", "password": password},
        ).status_code
        == 201
    )


def test_public_registration_cannot_set_admin_role(client: TestClient) -> None:
    password = token_urlsafe()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "listener",
            "email": "listener@example.com",
            "password": password,
            "role": "admin",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert password not in response.text


def test_invalid_credentials_do_not_distinguish_missing_account(client: TestClient) -> None:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "listener",
                "email": "listener@example.com",
                "password": token_urlsafe(),
            },
        ).status_code
        == 201
    )
    responses = [
        client.post("/api/v1/auth/login", json={"username": name, "password": "wrong-password"})
        for name in ("listener", "missing")
    ]
    assert all(response.status_code == 401 for response in responses)
    assert all(response.headers["WWW-Authenticate"] == "Bearer" for response in responses)
    assert responses[0].json() == responses[1].json()


@pytest.mark.parametrize("authorization", ["", "Basic invalid", "Bearer not-a-jwt"])
def test_invalid_bearer_is_401(client: TestClient, authorization: str) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": authorization})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_cli_creates_admin_without_promoting_existing_account(
    client: TestClient, database: Engine, test_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app import cli

    fields = iter(("operator", "operator@example.com", "listener", "listener@example.com"))
    password = token_urlsafe()
    account = {"username": "listener", "email": "listener@example.com", "password": password}
    assert client.post("/api/v1/auth/register", json=account).status_code == 201
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(fields))
    monkeypatch.setattr(cli, "getpass", lambda _prompt: password)
    monkeypatch.setattr(cli, "DatabaseSettings", lambda: test_settings)

    assert cli.create_admin() == 0
    assert cli.create_admin() == 1
    with Session(database) as session:
        assert session.scalar(select(User.role).where(User.username == "operator")) == Role.ADMIN
        assert session.scalar(select(User.role).where(User.username == "listener")) == Role.USER
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "operator", "password": password}
        ).status_code
        == 200
    )
