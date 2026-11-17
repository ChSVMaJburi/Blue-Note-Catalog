from datetime import date
from typing import Annotated, TypedDict

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, with_config

from app.models import MAX_ID


def without_null_byte(value: str) -> str:
    if "\x00" in value:
        raise ValueError("Text must not contain a null byte")
    return value


Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
    AfterValidator(without_null_byte),
]
Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=180),
    AfterValidator(without_null_byte),
]
Bio = Annotated[str, StringConstraints(max_length=4000), AfterValidator(without_null_byte)]
PositiveInteger = Annotated[int, Field(strict=True, gt=0, le=MAX_ID)]
FilterId = Annotated[int, Field(gt=0, le=MAX_ID)]
Search = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(without_null_byte),
]


class CatalogInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArtistCreate(CatalogInput):
    name: Name
    bio: Bio | None = None


class AlbumCreate(CatalogInput):
    artist_id: PositiveInteger
    title: Title
    release_date: date | None = None


class TrackCreate(CatalogInput):
    album_id: PositiveInteger
    title: Title
    track_number: PositiveInteger
    duration_seconds: PositiveInteger


patch_config = ConfigDict(extra="forbid", json_schema_extra={"minProperties": 1})


@with_config(patch_config)
class ArtistChanges(TypedDict, total=False):
    name: Name
    bio: Bio | None


@with_config(patch_config)
class AlbumChanges(TypedDict, total=False):
    artist_id: PositiveInteger
    title: Title
    release_date: date | None


@with_config(patch_config)
class TrackChanges(TypedDict, total=False):
    album_id: PositiveInteger
    title: Title
    track_number: PositiveInteger
    duration_seconds: PositiveInteger


def require_changes[Changes](changes: Changes) -> Changes:
    if not changes:
        raise ValueError("At least one field must be supplied")
    return changes


ArtistPatch = Annotated[ArtistChanges, AfterValidator(require_changes)]
AlbumPatch = Annotated[AlbumChanges, AfterValidator(require_changes)]
TrackPatch = Annotated[TrackChanges, AfterValidator(require_changes)]


class ArtistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    bio: str | None


class AlbumRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artist_id: int
    title: str
    release_date: date | None


class TrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    album_id: int
    title: str
    track_number: int
    duration_seconds: int


class ArtistFilters(CatalogInput):
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    offset: Annotated[int, Field(ge=0, le=MAX_ID)] = 0
    q: Search | None = None


class AlbumFilters(ArtistFilters):
    artist_id: FilterId | None = None


class TrackFilters(AlbumFilters):
    album_id: FilterId | None = None


class Page[Item](BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[Item]
    limit: int
    offset: int
    has_more: bool
