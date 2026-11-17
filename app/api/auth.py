from fastapi import APIRouter, Response

from app.api.dependencies import CurrentUser
from app.db import AppSettings, DbSession
from app.errors import error_docs
from app.models import User
from app.schemas.auth import LoginRequest, Registration, TokenResponse, UserResponse
from app.security import issue_access_token
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"], responses=error_docs(422, 500))


@router.post("/register", response_model=UserResponse, status_code=201, responses=error_docs(409))
def register(data: Registration, session: DbSession) -> User:
    return auth.create_account(session, data)


@router.post("/login", responses=error_docs(401))
def login(
    data: LoginRequest, session: DbSession, settings: AppSettings, response: Response
) -> TokenResponse:
    user = auth.authenticate(session, data)
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=issue_access_token(user.id, settings),
        expires_in=settings.access_token_minutes * 60,
    )


@router.get("/me", response_model=UserResponse, responses=error_docs(401))
def me(user: CurrentUser) -> User:
    return user
