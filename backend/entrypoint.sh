#!/bin/sh

set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! pg_isready -h postgres -p 5432 -U ${POSTGRES_USER:-postgres}; do
    sleep 1
done

echo "Database is ready"

# Initialize database
echo "Initializing database..."
if ! python init_db.py; then
    echo "Failed to initialize database"
    exit 1
fi

echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 "$@"