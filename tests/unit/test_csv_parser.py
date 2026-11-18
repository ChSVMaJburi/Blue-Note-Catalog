import pytest

from app.errors import AppError
from app.services.imports import MAX_FILE_BYTES, parse_csv

HEADER = b"album_id,title,track_number,duration_seconds\n"


def test_csv_line_numbers_and_quoted_fields():
    records, errors = parse_csv(
        b"\xef\xbb\xbf" + HEADER + b'1,"Blue,\nGreen",1,90\r\n1,No,two,3\r\n\r\n'
    )
    assert [(number, data.title) for number, data in records] == [(2, "Blue,\nGreen")]
    assert [(error.line, error.code) for error in errors] == [
        (4, "validation_error"),
        (5, "column_count"),
    ]


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "invalid_header"),
        (b"title,title,track_number,duration_seconds", "invalid_header"),
        (HEADER + b"\xff", "invalid_encoding"),
        (HEADER + b'1,"unfinished', "invalid_csv"),
        (HEADER + b"1,T,1,60\n" * 1001, "too_many_rows"),
        (b"x" * (MAX_FILE_BYTES + 1), "file_too_large"),
    ],
)
def test_whole_file_errors(content, code):
    with pytest.raises(AppError) as caught:
        parse_csv(content)
    assert caught.value.code == code


def test_header_only_and_reordered_columns():
    assert parse_csv(HEADER) == ([], [])
    records, errors = parse_csv(b"title,duration_seconds,album_id,track_number\nBlue,30,1,2")
    assert not errors
    assert records[0][1].track_number == 2
