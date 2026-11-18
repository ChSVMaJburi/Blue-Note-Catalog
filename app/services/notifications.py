import logging
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.repositories.subscriptions import recipients, track_details

logger = logging.getLogger("uvicorn.error.catalog.mail")


@dataclass(frozen=True, slots=True)
class TrackEmail:
    to: str
    subject: str
    body: str


def send_mock_email(message: TrackEmail) -> None:
    logger.info("Mock email accepted: subject=%r body=%r", message.subject, message.body)


def notify_subscribers(engine: Engine, track_ids: list[int]) -> None:
    with Session(engine) as session:
        tracks = track_details(session, track_ids)
    for artist_id, group in groupby(tracks, key=attrgetter("artist_id")):
        artist_tracks = list(group)
        after = 0
        while True:
            with Session(engine) as session:
                batch = recipients(session, artist_id, after, limit=200)
            if not batch:
                break
            for recipient in batch:
                for track in artist_tracks:
                    message = TrackEmail(
                        recipient.email,
                        f"Новый трек: {track.title}",
                        f"{track.name} — {track.title} (/api/v1/tracks/{track.id})",
                    )
                    try:
                        send_mock_email(message)
                    except Exception:
                        logger.error(
                            "Email delivery failed: track_id=%d user_id=%d", track.id, recipient.id
                        )
            after = batch[-1].id
