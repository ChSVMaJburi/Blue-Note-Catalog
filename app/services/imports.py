import csv
from io import StringIO

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import constraint_name
from app.errors import AppError
from app.models import Track
from app.repositories import catalog
from app.schemas.imports import CsvTrack, ImportReport, RowError

MAX_FILE_BYTES = 128 * 1024
MAX_ROWS = 1000
COLUMNS = ("album_id", "title", "track_number", "duration_seconds")


def parse_csv(content: bytes) -> tuple[list[tuple[int, CsvTrack]], list[RowError]]:
    if len(content) > MAX_FILE_BYTES:
        raise AppError(413, "file_too_large", "CSV exceeds 128 KiB")
    try:
        stream = StringIO(content.decode("utf-8-sig"), newline="")
    except UnicodeDecodeError:
        raise AppError(422, "invalid_encoding", "CSV must use UTF-8") from None

    reader = csv.reader(stream, strict=True)
    records = []
    errors = []
    try:
        header = next(reader, [])
        if sorted(header) != sorted(COLUMNS):
            raise AppError(422, "invalid_header", "Expected columns: " + ", ".join(COLUMNS))
        line = reader.line_num + 1
        for count, row in enumerate(reader, start=1):
            if count > MAX_ROWS:
                raise AppError(413, "too_many_rows", "CSV exceeds 1000 records")
            if len(row) != len(header):
                errors.append(
                    RowError(line=line, code="column_count", message="Expected four fields")
                )
            else:
                try:
                    data = CsvTrack.model_validate(dict(zip(header, row, strict=True)))
                    records.append((line, data))
                except ValidationError as error:
                    message = "; ".join(
                        f"{issue['loc'][0]}: {issue['msg']}" for issue in error.errors()
                    )
                    errors.append(RowError(line=line, code="validation_error", message=message))
            line = reader.line_num + 1
    except csv.Error:
        raise AppError(422, "invalid_csv", f"Malformed CSV near line {reader.line_num}") from None
    return records, errors


def import_tracks(session: Session, content: bytes) -> tuple[ImportReport, list[int]]:
    records, errors = parse_csv(content)
    saved_ids = []
    for line, data in records:
        try:
            with session.begin_nested():
                track = Track(**data.model_dump())
                catalog.add(session, track)
                session.flush()
            saved_ids.append(track.id)
        except IntegrityError as error:
            match constraint_name(error):
                case "uq_tracks_album_number":
                    code, message = "track_number_conflict", "Track number already used on album"
                case "fk_tracks_album_id_albums":
                    code, message = "album_not_found", "Album not found"
                case _:
                    raise
            errors.append(RowError(line=line, code=code, message=message))
    session.commit()
    report = ImportReport(
        imported=len(saved_ids),
        rejected=len(errors),
        errors=sorted(errors, key=lambda item: item.line),
    )
    return report, saved_ids
