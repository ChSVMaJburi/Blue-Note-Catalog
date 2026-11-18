#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

if [ ! -e .env ]; then
    umask 077
    temporary_env=$(mktemp .env.bootstrap.XXXXXXXX)
    trap 'rm -f "$temporary_env"' EXIT
    db_secret=$(openssl rand -hex 32)
    api_secret=$(openssl rand -hex 32)
    jwt_secret=$(openssl rand -hex 32)
    sed -e "s/^POSTGRES_PASSWORD=$/POSTGRES_PASSWORD=$db_secret/" \
        -e "s/^API_DB_PASSWORD=$/API_DB_PASSWORD=$api_secret/" \
        -e "s/^JWT_SECRET=$/JWT_SECRET=$jwt_secret/" .env.example > "$temporary_env"
    ln "$temporary_env" .env || [ -f .env ]
    rm -f "$temporary_env"
    trap - EXIT
fi

exec docker compose up --build --wait --wait-timeout 90
