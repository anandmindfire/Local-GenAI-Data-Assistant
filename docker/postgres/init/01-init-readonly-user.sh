#!/bin/sh
set -e

echo "Configuring restricted PostgreSQL read-only user..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create read-only role if it doesn't already exist
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${POSTGRES_READONLY_USER:-genai_readonly}') THEN
            CREATE ROLE ${POSTGRES_READONLY_USER:-genai_readonly} WITH LOGIN PASSWORD '${POSTGRES_READONLY_PASSWORD:-readonly_secret_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;
        END IF;
    END
    \$\$;

    -- Revoke all default privileges from public schema for security
    REVOKE CREATE ON SCHEMA public FROM PUBLIC;

    -- Grant CONNECT and USAGE
    GRANT CONNECT ON DATABASE ${POSTGRES_DB:-genai_db} TO ${POSTGRES_READONLY_USER:-genai_readonly};
    GRANT USAGE ON SCHEMA public TO ${POSTGRES_READONLY_USER:-genai_readonly};

    -- Grant SELECT ONLY on existing and future tables
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${POSTGRES_READONLY_USER:-genai_readonly};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ${POSTGRES_READONLY_USER:-genai_readonly};

    -- Enforce strict statement timeout (5 seconds) to prevent Denial of Service
    ALTER ROLE ${POSTGRES_READONLY_USER:-genai_readonly} SET statement_timeout = '5000ms';
EOSQL

echo "Restricted read-only user configured successfully."
