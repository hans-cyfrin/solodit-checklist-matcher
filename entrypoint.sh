#!/bin/bash

# Debug: Print all environment variables
echo "DEBUG: All environment variables:"
env | sort

# In Railway, use the internal DATABASE_URL
if [ "$RAILWAY_ENVIRONMENT" = "production" ]; then
    if [ -n "$DATABASE_URL" ]; then
        echo "Using Railway internal DATABASE_URL"
    else
        echo "WARNING: Internal DATABASE_URL not found, falling back to public URL"
        export DATABASE_URL="$DATABASE_PUBLIC_URL"
    fi
fi

echo "DEBUG: DATABASE_URL=$DATABASE_URL"

# Parse DATABASE_URL
if [ -n "$DATABASE_URL" ]; then
    # Extract connection details from DATABASE_URL
    PGUSER=$(echo $DATABASE_URL | awk -F[:/@] '{print $4}')
    PGPASSWORD=$(echo $DATABASE_URL | awk -F[:/@] '{print $5}')
    PGHOST=$(echo $DATABASE_URL | awk -F[:/@] '{print $6}')
    PGPORT=$(echo $DATABASE_URL | awk -F[:/@] '{print $7}' | awk -F/ '{print $1}')
    PGDATABASE=$(echo $DATABASE_URL | awk -F/ '{print $NF}')

    export PGUSER PGPASSWORD PGHOST PGPORT PGDATABASE

    echo "DEBUG: Parsed database connection details:"
    echo "PGHOST=$PGHOST"
    echo "PGPORT=$PGPORT"
    echo "PGUSER=$PGUSER"
    echo "PGDATABASE=$PGDATABASE"
else
    echo "ERROR: No DATABASE_URL found in environment variables!"
    exit 1
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
echo "Trying to connect to PostgreSQL at $PGHOST:$PGPORT..."
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER"; do
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