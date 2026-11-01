#!/bin/sh
# Idempotently initialize access to an EXISTING PostgreSQL database.
# This does not create or replace the database or its Docker volume.
set -eu

export PGHOST="$POSTGRES_HOST"
export PGPORT="$POSTGRES_PORT"
export PGDATABASE="$POSTGRES_DB"
export PGUSER="$POSTGRES_ADMIN_USER"
export PGPASSWORD="$POSTGRES_PASSWORD"

attempt=0
until pg_isready -q -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE"; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo 'Existing PostgreSQL did not become reachable. Check its Docker network, hostname and port.' >&2
        exit 1
    fi
    sleep 2
done

# psql's :'app_password' safely quotes the role password as a SQL string.
# Both CREATE and ALTER enforce the application's non-BYPASSRLS permissions.
psql -X -v ON_ERROR_STOP=1 -v "app_password=$PG_APP_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;

SELECT format(
    'CREATE ROLE proptech_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    :'app_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'proptech_app')
\gexec

SELECT format(
    'ALTER ROLE proptech_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    :'app_password'
)
\gexec

SELECT format('GRANT CONNECT ON DATABASE %I TO proptech_app', current_database())
\gexec
GRANT USAGE ON SCHEMA public TO proptech_app;
SQL

echo 'Existing database reachable; pgvector and proptech_app access prepared.'
