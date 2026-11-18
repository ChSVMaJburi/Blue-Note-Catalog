"""Exercise the running API over HTTP using disposable credentials."""

import json
import os
from secrets import token_hex, token_urlsafe
from urllib.request import Request, urlopen


def main() -> None:
    base = f"http://127.0.0.1:{int(os.environ.get('APP_PORT', '8000'))}"
    with urlopen(base + "/health/ready", timeout=5) as response:
        assert json.load(response) == {"status": "ok"}
    username = "smoke_" + token_hex(6)
    body = {"username": username, "email": f"{username}@example.com", "password": token_urlsafe()}
    request = Request(
        base + "/api/v1/auth/register",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        assert response.status == 201
        account = json.load(response)
        assert account["username"] == username and account["role"] == "user"
    print("Readiness and registration passed")


if __name__ == "__main__":
    main()
