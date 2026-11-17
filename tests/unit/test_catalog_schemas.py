import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.catalog import ArtistCreate, ArtistPatch, TrackCreate


@pytest.mark.parametrize(
    ("update", "expected"),
    [
        ({"name": " Nina Simone "}, {"name": "Nina Simone"}),
        ({"bio": None}, {"bio": None}),
    ],
)
def test_patch_distinguishes_omission_and_null(update: dict, expected: dict) -> None:
    assert TypeAdapter(ArtistPatch).validate_python(update) == expected


@pytest.mark.parametrize("changes", [{}, {"name": None}, {"id": 10}, {"name": "  "}])
def test_patch_rejects_invalid_changes(changes: dict) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(ArtistPatch).validate_python(changes)


@pytest.mark.parametrize("name", ["   ", "Contains\x00null", "x" * 161])
def test_artist_name_validation(name: str) -> None:
    with pytest.raises(ValidationError):
        ArtistCreate(name=name)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("album_id", -1),
        ("duration_seconds", 0),
        ("track_number", True),
        ("track_number", "1"),
        ("track_number", 2_147_483_648),
    ],
)
def test_track_numbers_respect_database_bounds(field: str, value: object) -> None:
    data = {"album_id": 1, "duration_seconds": 200, "track_number": 1, "title": "Autumn Leaves"}
    data[field] = value
    with pytest.raises(ValidationError) as caught:
        TrackCreate.model_validate(data)
    assert caught.value.errors()[0]["loc"] == (field,)
