from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, update

from app.models import Role, User

pytestmark = pytest.mark.integration
BASE = "/api/v1"


def create(client: TestClient, headers: dict[str, str], resource: str, data: dict) -> dict:
    response = client.post(f"{BASE}/{resource}", json=data, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_catalog_lifecycle(client: TestClient, admin_headers: dict[str, str]) -> None:
    artist = create(client, admin_headers, "artists", {"name": "Miles Davis", "bio": "Trumpeter"})
    album = create(
        client,
        admin_headers,
        "albums",
        {"artist_id": artist["id"], "title": "Kind of Blue", "release_date": "1959-08-17"},
    )
    track = create(
        client,
        admin_headers,
        "tracks",
        {"album_id": album["id"], "title": "So What", "track_number": 1, "duration_seconds": 562},
    )

    for resource, row, changes in [
        ("artists", artist, {"bio": None}),
        ("albums", album, {"release_date": None}),
        ("tracks", track, {"duration_seconds": 560}),
    ]:
        url = f"{BASE}/{resource}/{row['id']}"
        assert client.get(url).json() == row
        patched = client.patch(url, json=changes, headers=admin_headers)
        assert patched.status_code == 200, patched.text
        assert patched.json() == row | changes
        assert client.get(url).json() == row | changes

    for resource, row in [("artists", artist), ("albums", album)]:
        blocked = client.delete(f"{BASE}/{resource}/{row['id']}", headers=admin_headers)
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "resource_in_use"

    for resource, row in [("tracks", track), ("albums", album), ("artists", artist)]:
        url = f"{BASE}/{resource}/{row['id']}"
        deleted = client.delete(url, headers=admin_headers)
        assert deleted.status_code == 204
        assert deleted.content == b""
        assert client.get(url).status_code == 404


def test_parent_and_unique_constraints_map_to_http_errors(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    missing_artist = client.post(
        f"{BASE}/albums", headers=admin_headers, json={"artist_id": 900, "title": "Missing Artist"}
    )
    assert missing_artist.status_code == 404
    assert missing_artist.json()["error"]["code"] == "artist_not_found"

    artist = create(client, admin_headers, "artists", {"name": "John Coltrane"})
    album_data = {"artist_id": artist["id"], "title": "Blue Train"}
    album = create(client, admin_headers, "albums", album_data)
    duplicate = client.post(f"{BASE}/albums", json=album_data, headers=admin_headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "album_title_conflict"

    track_data = {
        "album_id": album["id"],
        "title": "Blue Train",
        "track_number": 1,
        "duration_seconds": 645,
    }
    missing_album = client.post(
        f"{BASE}/tracks", json=track_data | {"album_id": 900}, headers=admin_headers
    )
    assert missing_album.status_code == 404
    assert missing_album.json()["error"]["code"] == "album_not_found"
    create(client, admin_headers, "tracks", track_data)
    second = create(client, admin_headers, "tracks", track_data | {"track_number": 2})
    url = f"{BASE}/tracks/{second['id']}"

    rejected = client.patch(url, json={"track_number": 1}, headers=admin_headers)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "track_number_conflict"
    assert client.get(url).json() == second


def test_search_pagination_and_relationship_filters(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    first = create(client, admin_headers, "artists", {"name": "Bill Evans"})
    second = create(client, admin_headers, "artists", {"name": "Ella Fitzgerald"})
    first_album = create(
        client, admin_headers, "albums", {"artist_id": first["id"], "title": "Everybody Digs"}
    )
    second_album = create(
        client, admin_headers, "albums", {"artist_id": second["id"], "title": "Song Book"}
    )
    track_data = {"title": "Night_1", "track_number": 1, "duration_seconds": 200}
    first_track = create(
        client, admin_headers, "tracks", track_data | {"album_id": first_album["id"]}
    )
    second_track = create(
        client,
        admin_headers,
        "tracks",
        track_data | {"album_id": second_album["id"], "title": "Night X"},
    )

    first_page = client.get(f"{BASE}/tracks", params={"limit": 1}).json()
    second_page = client.get(f"{BASE}/tracks", params={"limit": 1, "offset": 1}).json()
    assert first_page == {"items": [first_track], "limit": 1, "offset": 0, "has_more": True}
    assert second_page == {"items": [second_track], "limit": 1, "offset": 1, "has_more": False}
    assert client.get(f"{BASE}/artists", params={"q": "eVaNs"}).json()["items"] == [first]
    assert client.get(f"{BASE}/albums", params={"artist_id": second["id"]}).json()["items"] == [
        second_album
    ]
    assert client.get(f"{BASE}/tracks", params={"q": "NiGhT_"}).json()["items"] == [first_track]
    assert client.get(f"{BASE}/tracks", params={"q": "%"}).json()["items"] == []
    assert client.get(f"{BASE}/tracks", params={"artist_id": first["id"]}).json()["items"] == [
        first_track
    ]
    assert (
        client.get(
            f"{BASE}/tracks", params={"artist_id": first["id"], "album_id": second_album["id"]}
        ).json()["items"]
        == []
    )


@pytest.mark.parametrize("resource", ["artists", "albums", "tracks"])
def test_mutations_require_admin(
    client: TestClient, make_user: Callable[[], dict[str, str]], resource: str
) -> None:
    user_headers = make_user()
    for method, path in [
        ("POST", resource),
        ("PATCH", f"{resource}/1"),
        ("DELETE", f"{resource}/1"),
    ]:
        anonymous = client.request(method, f"{BASE}/{path}")
        forbidden = client.request(method, f"{BASE}/{path}", headers=user_headers)
        assert anonymous.status_code == 401
        assert anonymous.headers["WWW-Authenticate"] == "Bearer"
        assert forbidden.status_code == 403
        assert forbidden.json()["error"]["code"] == "forbidden"


def test_removing_admin_role_takes_effect_on_existing_token(
    client: TestClient, database: Engine, admin_headers: dict[str, str]
) -> None:
    with database.begin() as connection:
        connection.execute(update(User).where(User.username == "operator").values(role=Role.USER))
    response = client.post(f"{BASE}/artists", headers=admin_headers, json={"name": "Sonny Rollins"})
    assert response.status_code == 403


def test_validation_error_contract(client: TestClient, admin_headers: dict[str, str]) -> None:
    query = client.get(f"{BASE}/tracks", params={"limit": 101})
    assert query.status_code == 422
    assert query.json()["error"]["details"][0]["location"] == ["query", "limit"]

    payload = client.post(
        f"{BASE}/tracks",
        headers=admin_headers,
        json={"album_id": 1, "title": "Track", "duration_seconds": 60, "track_number": "1"},
    )
    assert payload.status_code == 422
    assert payload.json()["error"]["details"][0]["location"] == ["body", "track_number"]

    artist = create(client, admin_headers, "artists", {"name": "Nina Simone"})
    for patch in ({}, {"name": None}, {"id": 999}):
        response = client.patch(f"{BASE}/artists/{artist['id']}", json=patch, headers=admin_headers)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
    assert client.get(f"{BASE}/artists/0").status_code == 422
    missing = client.get(f"{BASE}/not-a-route")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "route_not_found"
