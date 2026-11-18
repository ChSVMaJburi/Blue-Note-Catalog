from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
)

from app.models import Role

Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$"
    ),
    AfterValidator(str.lower),
]


def validate_new_password(password: SecretStr) -> SecretStr:
    if not password.get_secret_value().strip():
        raise ValueError("Password must not be blank")
    return password


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Username
    password: Annotated[SecretStr, Field(min_length=1, max_length=128)]


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Username
    email: Annotated[EmailStr, Field(max_length=254), AfterValidator(str.lower)]
    password: Annotated[
        SecretStr, Field(min_length=12, max_length=128), AfterValidator(validate_new_password)
    ]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: Role
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
