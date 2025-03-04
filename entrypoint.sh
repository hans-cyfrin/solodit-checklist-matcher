#!/bin/bash

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -d "$DATABASE_URL"; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

# Create pgvector extension
echo "Creating pgvector extension..."
psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# Initialize database
echo "Initializing database..."
python init_db.py

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT