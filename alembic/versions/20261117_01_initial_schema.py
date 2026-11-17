"""Create the catalog, accounts, and personal collections.

Revision ID: 20261117_01
"""

import sqlalchemy as sa

from alembic import op

revision = "20261117_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(5), nullable=False, server_default=sa.text("'user'")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
        sa.CheckConstraint("role IN ('user', 'admin')", name=op.f("ck_users_valid_role")),
    )
    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("bio", sa.Text()),
    )
    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "artist_id",
            sa.Integer(),
            sa.ForeignKey("artists.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("release_date", sa.Date()),
        sa.UniqueConstraint("artist_id", "title", name="uq_albums_artist_title"),
    )
    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "album_id",
            sa.Integer(),
            sa.ForeignKey("albums.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("track_number", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.UniqueConstraint("album_id", "track_number", name="uq_tracks_album_number"),
        sa.CheckConstraint("track_number > 0", name=op.f("ck_tracks_positive_track_number")),
        sa.CheckConstraint("duration_seconds > 0", name=op.f("ck_tracks_positive_duration")),
    )
    op.create_table(
        "subscriptions",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "artist_id",
            sa.Integer(),
            sa.ForeignKey("artists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_subscriptions_artist_id", "subscriptions", ["artist_id"])
    op.create_table(
        "playlists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_playlists_owner_id", "playlists", ["owner_id"])
    op.create_table(
        "playlist_tracks",
        sa.Column(
            "playlist_id",
            sa.Integer(),
            sa.ForeignKey("playlists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "track_id",
            sa.Integer(),
            sa.ForeignKey("tracks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_playlist_tracks_track_id", "playlist_tracks", ["track_id"])


def downgrade() -> None:
    for table in (
        "playlist_tracks",
        "playlists",
        "subscriptions",
        "tracks",
        "albums",
        "artists",
        "users",
    ):
        op.drop_table(table)
