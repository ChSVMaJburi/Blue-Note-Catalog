import pytest

from app.services import notifications
from app.services.imports import MAX_FILE_BYTES

pytestmark = pytest.mark.integration
PATH = "/api/v1/tracks/import"
HEADER = b"album_id,title,track_number,duration_seconds\n"


def test_import_partial_success_and_notifications(client, admin_headers, make_user, monkeypatch):
    fan = make_user()
    artist = client.post("/api/v1/artists", headers=admin_headers, json={"name": "Ella"}).json()
    album = client.post(
        "/api/v1/albums", headers=admin_headers, json={"title": "Blue", "artist_id": artist["id"]}
    ).json()
    assert client.put(f"/api/v1/me/subscriptions/{artist['id']}", headers=fan).status_code == 204
    messages = []
    monkeypatch.setattr(notifications, "send_mock_email", messages.append)
    data = (
        HEADER
        + (
            f"{album['id']},First,1,30\n{album['id']},Duplicate,1,10\n"
            f"{album['id']},Invalid,2,0\n999,Missing,2,30\n{album['id']},Second,2,40\n"
        ).encode()
    )
    files = {"file": ("tracks.csv", data, "text/csv")}
    response = client.post(PATH, headers=admin_headers, files=files)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["imported"], result["rejected"]) == (2, 3)
    assert [(error["line"], error["code"]) for error in result["errors"]] == [
        (3, "track_number_conflict"),
        (4, "validation_error"),
        (5, "album_not_found"),
    ]
    assert [message.to for message in messages] == ["listener@example.com"] * 2
    assert [track["title"] for track in client.get("/api/v1/tracks").json()["items"]] == [
        "First",
        "Second",
    ]
    assert client.post(PATH, headers=admin_headers, files=files).json()["imported"] == 0
    assert len(messages) == 2


def test_import_access_and_file_errors(client, admin_headers, make_user):
    files = {"file": ("tracks.csv", HEADER)}
    assert client.post(PATH, files=files).status_code == 401
    assert client.post(PATH, files=files, headers=make_user()).status_code == 403
    assert client.post(PATH, headers=admin_headers, json={}).status_code == 415
    for name, content, code in [
        ("other.txt", HEADER, 422),
        ("empty.csv", b"", 422),
        ("bad.csv", b'"malformed header', 422),
        ("oversize.csv", b"x" * (MAX_FILE_BYTES + 1), 413),
        ("larger.csv", b"x" * (MAX_FILE_BYTES * 2), 413),
    ]:
        response = client.post(PATH, headers=admin_headers, files={"file": (name, content)})
        assert response.status_code == code, response.text
    assert client.get("/api/v1/tracks").json()["items"] == []


def test_unclosed_quote_preserves_complete_records(client, admin_headers, make_user, monkeypatch):
    artist = client.post("/api/v1/artists", headers=admin_headers, json={"name": "Ella"}).json()
    album = client.post(
        "/api/v1/albums", headers=admin_headers, json={"title": "Blue", "artist_id": artist["id"]}
    ).json()
    assert (
        client.put(f"/api/v1/me/subscriptions/{artist['id']}", headers=make_user()).status_code
        == 204
    )
    sent = []
    monkeypatch.setattr(notifications, "send_mock_email", sent.append)
    data = HEADER + f'{album["id"]},"Two\nlines",1,30\n1,"unfinished\n1,Later,2,60'.encode()
    result = client.post(PATH, headers=admin_headers, files={"file": ("tracks.csv", data)})
    assert result.status_code == 200
    assert result.json() == {
        "imported": 1,
        "rejected": 1,
        "errors": [
            {
                "line": 4,
                "code": "invalid_csv",
                "message": "Malformed CSV record; parsing stopped here",
            }
        ],
    }
    assert [item["title"] for item in client.get("/api/v1/tracks").json()["items"]] == [
        "Two\nlines"
    ]
    assert len(sent) == 1
