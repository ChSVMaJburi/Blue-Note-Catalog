import pytest

from app.services import notifications

pytestmark = pytest.mark.integration


def test_subscription_delivery_and_failure_isolation(client, make_user, admin_headers, monkeypatch):
    fans = [make_user(name) for name in ("first", "second", "unsubscribed")]
    artist = client.post("/api/v1/artists", json={"name": "Ella"}, headers=admin_headers).json()
    album = client.post(
        "/api/v1/albums", json={"artist_id": artist["id"], "title": "Live"}, headers=admin_headers
    ).json()
    listing = "/api/v1/me/subscriptions"
    path = f"{listing}/{artist['id']}"
    assert client.put(path).status_code == 401
    assert client.put(listing + "/999", headers=fans[0]).status_code == 404
    for fan in fans:
        assert client.put(path, headers=fan).status_code == 204
    assert client.put(path, headers=fans[0]).status_code == 204
    assert client.get(listing, headers=fans[0]).json()["items"] == [artist]
    for _ in range(2):
        assert client.delete(path, headers=fans[-1]).status_code == 204
    assert client.get(listing, headers=fans[-1]).json()["items"] == []
    messages = []

    def deliver(message):
        messages.append(message)
        if message.to == "first@example.com":
            raise OSError("Unavailable")

    monkeypatch.setattr(notifications, "send_mock_email", deliver)
    track = {"album_id": album["id"], "title": "Blue", "track_number": 1, "duration_seconds": 60}
    response = client.post("/api/v1/tracks", json=track, headers=admin_headers)
    assert response.status_code == 201
    assert client.get(f"/api/v1/tracks/{response.json()['id']}").json()["title"] == "Blue"
    assert client.post("/api/v1/tracks", json=track, headers=admin_headers).status_code == 409
    assert [message.to for message in messages] == ["first@example.com", "second@example.com"]
    assert all("Ella — Blue" in message.body for message in messages)
