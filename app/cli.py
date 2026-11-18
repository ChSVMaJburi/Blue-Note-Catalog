import argparse
import sys
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import DatabaseSettings
from app.db import make_engine
from app.errors import AppError
from app.models import Role
from app.schemas.auth import Registration
from app.services.auth import create_account


def create_admin() -> int:
    if not sys.stdin.isatty():
        print("Administrator creation requires an interactive terminal.", file=sys.stderr)
        return 1

    username = input("Username: ")
    email = input("Email: ")
    password = getpass("Password: ")
    if password != getpass("Repeat password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1

    try:
        registration = Registration(username=username, email=email, password=password)
        engine = make_engine(DatabaseSettings())
        try:
            with Session(engine, expire_on_commit=False) as session:
                user = create_account(session, registration, role=Role.ADMIN)
        finally:
            engine.dispose()
    except ValidationError as error:
        for issue in error.errors(include_input=False, include_context=False, include_url=False):
            print(f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}", file=sys.stderr)
        return 1
    except AppError as error:
        print(error.message, file=sys.stderr)
        return 1

    print(f"Administrator created: {user.username}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local catalog administration")
    parser.add_argument("command", choices=["create-admin"])
    parser.parse_args()
    return create_admin()


if __name__ == "__main__":
    sys.exit(main())
