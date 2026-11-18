import csv
from io import StringIO

from pydantic import ValidationError

from app.errors import AppError
from app.schemas.imports import CsvTrack, RowError

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
    except csv.Error:
        raise AppError(422, "invalid_header", "Malformed CSV header") from None
    if sorted(header) != sorted(COLUMNS):
        raise AppError(422, "invalid_header", "Expected columns: " + ", ".join(COLUMNS))
    while True:
        line = reader.line_num + 1
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error:
            row = None
        if len(records) + len(errors) >= MAX_ROWS:
            raise AppError(413, "too_many_rows", "CSV exceeds 1000 records")
        if row is None:
            errors.append(
                RowError(
                    line=line,
                    code="invalid_csv",
                    message="Malformed CSV record; parsing stopped here",
                )
            )
            break
        if len(row) != len(header):
            errors.append(RowError(line=line, code="column_count", message="Expected four fields"))
            continue
        try:
            data = CsvTrack.model_validate(dict(zip(header, row, strict=True)))
            records.append((line, data))
        except ValidationError as error:
            message = "; ".join(f"{issue['loc'][0]}: {issue['msg']}" for issue in error.errors())
            errors.append(RowError(line=line, code="validation_error", message=message))
    return records, errors
