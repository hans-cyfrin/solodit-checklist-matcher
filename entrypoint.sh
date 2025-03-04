#!/bin/bash

# Debug: Print all environment variables
echo "DEBUG: All environment variables:"
env | sort

echo "DEBUG: Current DATABASE_URL=$DATABASE_URL"

# In Railway, ensure we're using the correct database URL
if [ "$RAILWAY_ENVIRONMENT" = "production" ]; then
    if [[ "$DATABASE_URL" == *"postgres.railway.internal"* ]]; then
        echo "Using Railway internal DATABASE_URL"
    elif [[ "$DATABASE_URL" == *"postgres:admin@postgres"* ]]; then
        echo "ERROR: Found local development DATABASE_URL in production!"
        echo "Please remove the DATABASE_URL variable from Railway and link the PostgreSQL service's DATABASE_URL instead."
        exit 1
    elif [ -n "$DATABASE_PUBLIC_URL" ]; then
        echo "WARNING: Using public DATABASE_URL as fallback"
        export DATABASE_URL="$DATABASE_PUBLIC_URL"
    else
        echo "ERROR: No valid PostgreSQL URL found!"
        echo "Please make sure to:"
        echo "1. Add a PostgreSQL service in Railway"
        echo "2. Link the PostgreSQL service's DATABASE_URL to this application"
        echo "3. Remove any manually added DATABASE_URL variables"
        exit 1
    fi
fi

echo "DEBUG: Final DATABASE_URL=$DATABASE_URL"

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