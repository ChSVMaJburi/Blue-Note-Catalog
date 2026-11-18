from pydantic import BaseModel, field_validator

from app.schemas.catalog import TrackCreate


class CsvTrack(TrackCreate):
    @field_validator("album_id", "track_number", "duration_seconds", mode="before")
    @classmethod
    def decimal_integer(cls, value: str) -> int:
        digits = value.strip()
        if not (digits.isascii() and digits.isdecimal() and len(digits) <= 10):
            raise ValueError("Expected a positive decimal integer of at most 10 digits")
        return int(digits)


class RowError(BaseModel):
    line: int
    code: str
    message: str


class ImportReport(BaseModel):
    imported: int
    rejected: int
    errors: list[RowError]
