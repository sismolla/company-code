#!/usr/bin/env bash
set -e

# Wait for Postgres
until nc -z -v -w30 "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
  echo "⏳ Waiting for Postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  sleep 2
done

echo "✅ Database is up"

# Optional: run migrations & collectstatic before starting
python manage.py migrate --noinput || true
python manage.py collectstatic --noinput || true

echo "🚀 Starting: $@"
exec "$@"
