import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session

from alembic import command
from app.config import Settings
from app.models import Album, Artist, Base, Playlist, PlaylistTrack, Subscription, Track, User
from app.provision import API_ROLE, provision_role

pytestmark = pytest.mark.integration


def test_migration_downgrade_and_upgrade(
    database: Engine, migration_config: Config, test_settings: Settings
) -> None:
    try:
        command.downgrade(migration_config, "base")
        assert set(inspect(database).get_table_names()).isdisjoint(Base.metadata.tables)
    finally:
        command.upgrade(migration_config, "head")
        provision_role(test_settings, test_settings.postgres_password.get_secret_value())
    assert set(Base.metadata.tables) <= set(inspect(database).get_table_names())
    command.check(migration_config)


def test_runtime_role_has_only_application_privileges(database: Engine) -> None:
    from sqlalchemy import text

    with database.connect() as connection:
        permissions = connection.execute(
            text("""
                SELECT rolsuper, rolcreaterole, rolcreatedb,
                       has_schema_privilege(rolname, 'public', 'CREATE'),
                       has_column_privilege(rolname, 'users', 'role', 'INSERT'),
                       has_column_privilege(rolname, 'users', 'role', 'UPDATE'),
                       has_table_privilege(rolname, 'artists', 'TRUNCATE'),
                       has_table_privilege(rolname, 'alembic_version', 'UPDATE')
                FROM pg_roles WHERE rolname = :role
            """),
            {"role": API_ROLE},
        ).one()
        assert not any(permissions)


def test_association_cleanup_enforced_by_postgres(database: Engine) -> None:
    with Session(database) as session:
        artist = Artist(name="Charlie Parker")
        user = User(username="listener", email="listener@example.com", password_hash="unused")
        session.add_all([artist, user])
        session.flush()
        album = Album(artist_id=artist.id, title="Yardbird")
        playlist = Playlist(owner_id=user.id, name="Favorites")
        session.add_all([album, playlist])
        session.flush()
        track = Track(
            album_id=album.id, title="Billie's Bounce", track_number=1, duration_seconds=190
        )
        session.add(track)
        session.flush()
        session.add_all(
            [
                Subscription(user_id=user.id, artist_id=artist.id),
                PlaylistTrack(playlist_id=playlist.id, track_id=track.id),
            ]
        )
        session.commit()

        session.delete(track)
        session.commit()
        assert session.scalar(select(PlaylistTrack)) is None
        assert session.scalar(select(Playlist)) is not None
        assert session.scalar(select(Subscription)) is not None

        session.delete(user)
        session.commit()
        assert session.scalar(select(Playlist)) is None
        assert session.scalar(select(Subscription)) is None
        assert session.scalar(select(Artist)) is not None
