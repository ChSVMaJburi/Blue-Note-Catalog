import pytest

pytestmark = pytest.mark.integration
URL = "/api/v1/me/playlists"


def test_playlist_private_lifecycle(client, make_user, admin_headers):
    owner = make_user("owner")
    stranger = make_user("other")
    assert client.get(URL).status_code == 401
    created = client.post(URL, json={"name": "Favorites"}, headers=owner)
    assert created.status_code == 201
    path = f"{URL}/{created.json()['id']}"
    assert client.get(URL, headers=stranger).json()["items"] == []
    for method, suffix, body in [
        ("GET", "", None),
        ("PATCH", "", {"name": "Other"}),
        ("DELETE", "", None),
        ("GET", "/tracks", None),
        ("PUT", "/tracks/1", None),
        ("DELETE", "/tracks/1", None),
    ]:
        assert client.request(method, path + suffix, json=body, headers=stranger).status_code == 404
    assert client.get(path, headers=owner).json()["name"] == "Favorites"
    assert client.patch(path, json={"name": "Evening"}, headers=owner).json()["name"] == "Evening"
    assert client.put(path + "/tracks/999", headers=owner).status_code == 404
    artist = client.post("/api/v1/artists", headers=admin_headers, json={"name": "Ella"}).json()
    album = client.post(
        "/api/v1/albums", headers=admin_headers, json={"artist_id": artist["id"], "title": "Live"}
    ).json()
    track = client.post(
        "/api/v1/tracks",
        headers=admin_headers,
        json={"album_id": album["id"], "title": "Blue", "track_number": 1, "duration_seconds": 200},
    ).json()
    member = f"{path}/tracks/{track['id']}"
    for _ in range(2):
        assert client.put(member, headers=owner).status_code == 204
    assert client.get(path + "/tracks", headers=owner).json()["items"] == [track]
    for _ in range(2):
        assert client.delete(member, headers=owner).status_code == 204
    assert client.get(path + "/tracks", headers=owner).json()["items"] == []
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
