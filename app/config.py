from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    postgres_host: str = "localhost"
    postgres_port: Annotated[int, Field(ge=1, le=65535)] = 5432
    postgres_db: str = "music_catalog"
    postgres_user: str = "catalog"
    postgres_password: Annotated[SecretStr, Field(min_length=1)]

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


class Settings(DatabaseSettings):
    jwt_secret: Annotated[SecretStr, Field(min_length=32)]
    access_token_minutes: Annotated[int, Field(ge=1, le=60)] = 30

    @field_validator("jwt_secret")
    @classmethod
    def reject_blank_secret(cls, secret: SecretStr) -> SecretStr:
        if not secret.get_secret_value().strip():
            raise ValueError("JWT secret must not be blank")
        return secret
