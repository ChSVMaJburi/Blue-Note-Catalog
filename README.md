# Blue Note Catalog

Jazz catalog REST API with FastAPI, SQLAlchemy 2, PostgreSQL 17 and Alembic. Catalog reads are public; only administrators can change catalog data. This branch implements the first milestone: accounts, catalog CRUD and the schema for playlists and subscriptions. Playlist/subscription endpoints, email delivery and CSV import are not yet implemented.

## Quick start

Requires Docker Engine and Docker Compose v2 or later. On a fresh checkout, generate a local `.env` once (requires OpenSSL):

```bash
(umask 077; set -C
  sed -e "s/^POSTGRES_PASSWORD=$/POSTGRES_PASSWORD=$(openssl rand -hex 24)/" \
      -e "s/^JWT_SECRET=$/JWT_SECRET=$(openssl rand -hex 32)/" .env.example > .env
)
docker compose up --build --wait
curl --fail http://localhost:8000/health/ready
```

If `.env` already exists, keep it and run only the last two commands. Alternatively copy `.env.example` and fill both empty secrets with independently generated random values. Compose waits for PostgreSQL, runs `alembic upgrade head` once, then starts the API. Swagger UI: <http://localhost:8000/docs>. The API binds to localhost; the database is not published to the host. `docker compose down` stops the stack without deleting its data.

| Setting | Purpose |
| --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER` | Database and login, default `music_catalog` / `catalog` |
| `POSTGRES_PASSWORD` | Required; no default |
| `JWT_SECRET` | Required; use an independently generated value with at least 32 random bytes |
| `ACCESS_TOKEN_MINUTES` | Optional; 1–60, default 30 |
| `APP_PORT` | Local HTTP port, default 8000 |

`POSTGRES_HOST` and `POSTGRES_PORT` are also supported by the app. Compose sets the host to `db`; the port defaults to 5432. PostgreSQL initialization variables only apply to an empty volume. Editing a password in `.env` does not rotate an existing database credential.

## API examples

Base path: `/api/v1`. Run the administrative command from a terminal:

```bash
docker compose exec api python -m app.cli create-admin
```

It creates a new Admin account, prompts twice for a hidden password, and never promotes an existing User. Public registration always creates a User. Try these requests in Swagger UI (passwords are entered locally, not passed as shell arguments):

| Request | Example JSON or query | Expected result |
| --- | --- | --- |
| `POST /auth/register` | `{"username":"listener","email":"listener@example.com","password":"<your unique password>"}` | `201`, account profile |
| `POST /auth/login` | `{"username":"<your admin username>","password":"<your admin password>"}` | `200`, bearer token |
| `GET /auth/me` | Paste the access token into Swagger's Authorize dialog | `200`, current profile |
| `POST /artists` | `{"name":"Miles Davis","bio":"Jazz trumpeter"}` | `201`, artist |
| `POST /albums` | `{"artist_id":1,"title":"Kind of Blue","release_date":"1959-08-17"}` | `201`, album |
| `POST /tracks` | `{"album_id":1,"title":"So What","track_number":1,"duration_seconds":562}` | `201`, track |
| `GET /tracks?q=so&artist_id=1&album_id=1&limit=10&offset=0` | No token required | `200`, page of tracks |
| `PATCH /artists/1` | `{"bio":null}` | `200`, bio cleared |
| `DELETE /tracks/1` | No body | `204`, empty response |

Use the IDs returned by the create calls in subsequent requests. All three collections also support `GET /{id}`, `PATCH /{id}` and `DELETE /{id}`. Lists are ordered by ID and return `items`, `limit`, `offset`, `has_more`. Search `q` is a literal case-insensitive substring of the name/title; filters combine with AND.

```json
{"error":{"code":"resource_in_use","message":"Remove dependent catalog entries first","details":[]}}
```

`401` means credentials are missing or invalid (`WWW-Authenticate: Bearer`); `403` means the authenticated user lacks permission. `404` covers missing resources/parents, `409` conflicts or dependent catalog records, and `422` invalid bodies or parameters. Validation details include location, code and message, not the submitted input.

## Migrations and tests

```bash
docker compose exec api alembic current
docker compose exec api alembic check
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml down
```

The test stack runs unit and HTTP integration tests on an isolated PostgreSQL instance with ephemeral storage and no published ports. It applies Alembic, exercises downgrade and re-upgrade, and checks ORM/migration consistency. Do not run destructive downgrades against a database with data you want to keep.

For unit tests and lint without Docker, use Python 3.13:

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest -q tests/unit
ruff check .
ruff format --check .
```

## Design choices

- Routers handle HTTP, schemas define the API contract, services decide outcomes and commit writes, and repositories build SQLAlchemy queries. A synchronous session per request keeps the transaction boundary explicit; sync handlers run outside the event loop.
- An album has one artist, a track has one album, and track authorship is derived through the album. Standalone tracks can use a single-track album; collaborations and multi-disc numbering are out of scope. Artist names need not be unique; album titles are unique per artist and track numbers per album.
- Core catalog deletes use `RESTRICT`; association cleanup uses `CASCADE`. PostgreSQL enforces invariants under concurrent writes; known constraint violations map to domain errors without a race-prone preflight query.
- Passwords are Argon2id hashes. JWTs are signed with HS256 and expire; role is read from PostgreSQL on protected requests rather than trusted from the token. No refresh tokens or per-token revocation in this milestone.
- Offset pagination is simple for a small catalog. Fetching one extra row avoids a separate count query; deep offsets and concurrent insert/delete can make offsets less useful. For larger datasets, evaluate keyset pagination and a trigram index based on measured query plans.
- The runtime image is multi-stage and non-root. The Compose credentials are for local development. For public deployment, add TLS, proper secret injection, separate application/migration database privileges, and protection against abusive login traffic.
