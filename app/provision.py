"""Apply migrations and provision the HTTP service in its dedicated PostgreSQL database."""

import os

import psycopg
from alembic.config import Config
from psycopg import sql

from alembic import command
from app.config import DatabaseSettings

API_ROLE = "music_catalog_api"


def main() -> None:
    settings = DatabaseSettings()
    api_password = os.environ["API_DB_PASSWORD"]
    command.upgrade(Config("alembic.ini"), "head")
    provision_role(settings, api_password)


def provision_role(settings: DatabaseSettings, api_password: str) -> None:
    if not api_password or settings.postgres_user == API_ROLE:
        raise ValueError("Provide a separate API database role and password")
    with psycopg.connect(
        dbname=settings.postgres_db,
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
    ) as connection:
        role = sql.Identifier(API_ROLE)
        existing = connection.execute(
            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname = %s",
            (API_ROLE,),
        ).fetchone()
        if existing is None:
            connection.execute(sql.SQL("CREATE ROLE {} LOGIN").format(role))
        elif any(existing):
            raise ValueError("API database role already has privileged attributes")
        connection.pgconn.change_password(API_ROLE.encode(), api_password.encode())
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        connection.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON artists, albums, tracks TO {}").format(
                role
            )
        )
        connection.execute(
            sql.SQL("GRANT SELECT, INSERT, DELETE, UPDATE (name) ON playlists TO {}").format(role)
        )
        connection.execute(
            sql.SQL("GRANT SELECT, INSERT, DELETE ON playlist_tracks TO {}").format(role)
        )
        connection.execute(sql.SQL("GRANT USAGE ON SEQUENCE playlists_id_seq TO {}").format(role))
        connection.execute(
            sql.SQL("GRANT SELECT, INSERT (username, email, password_hash) ON users TO {}").format(
                role
            )
        )
        connection.execute(
            sql.SQL(
                "GRANT USAGE ON SEQUENCE artists_id_seq, albums_id_seq, tracks_id_seq, "
                "users_id_seq TO {}"
            ).format(role)
        )


if __name__ == "__main__":
    main()
