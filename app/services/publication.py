from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import constraint_name
from app.errors import AppError
from app.models import Track
from app.schemas.catalog import TrackCreate
from app.schemas.imports import ImportReport, RowError
from app.services.imports import parse_csv


class TrackPublisher:
    def __init__(self, session: Session, enqueue: Callable[[list[int]], None]) -> None:
        self.session = session
        self.enqueue = enqueue

    def _insert(self, data: TrackCreate) -> Track:
        track = Track(**data.model_dump())
        self.session.add(track)
        try:
            self.session.flush()
        except IntegrityError as error:
            match constraint_name(error):
                case "uq_tracks_album_number":
                    raise AppError(
                        409, "track_number_conflict", "Track number already used on album"
                    ) from None
                case "fk_tracks_album_id_albums":
                    raise AppError(404, "album_not_found", "Album not found") from None
                case _:
                    raise
        return track

    def _publish(self, ids: list[int]) -> None:
        self.session.commit()
        if ids:
            self.enqueue(ids)

    def create(self, data: TrackCreate) -> Track:
        track = self._insert(data)
        self._publish([track.id])
        return track

    def import_csv(self, content: bytes) -> ImportReport:
        records, errors = parse_csv(content)
        saved_ids = []
        for line, data in records:
            try:
                with self.session.begin_nested():
                    track = self._insert(data)
                saved_ids.append(track.id)
            except AppError as error:
                errors.append(RowError(line=line, code=error.code, message=error.message))
        self._publish(saved_ids)
        return ImportReport(
            imported=len(saved_ids),
            rejected=len(errors),
            errors=sorted(errors, key=lambda item: item.line),
        )
