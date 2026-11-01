#!/usr/bin/env bash
set -euo pipefail
# Only executes on an empty PostgreSQL data volume.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v app_password="$PG_APP_PASSWORD" <<'SQL'
CREATE ROLE proptech_app LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE proptech TO proptech_app;
SQL
