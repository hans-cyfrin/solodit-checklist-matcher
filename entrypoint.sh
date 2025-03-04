#!/bin/bash

# Target database name
TARGET_DB_NAME="solodit_checklist"

# Debug: Print all environment variables
echo "DEBUG: All environment variables:"
env | sort

echo "DEBUG: Current DATABASE_URL=$DATABASE_URL"

# In Railway, ensure we're using the correct database URL
if [ "$RAILWAY_ENVIRONMENT" = "production" ]; then
    if [[ "$DATABASE_URL" == *"postgres.railway.internal"* ]]; then
        echo "Using Railway internal DATABASE_URL"

        # Save the original DATABASE_URL for admin connection
        ADMIN_DB_URL="$DATABASE_URL"

        # Get the current database name from the URL
        CURRENT_DB_NAME=$(echo $DATABASE_URL | awk -F/ '{print $NF}')
        echo "Current database name in URL: $CURRENT_DB_NAME"

        # If the database in the URL is not our target database, we'll need to create it
        if [ "$CURRENT_DB_NAME" != "$TARGET_DB_NAME" ]; then
            echo "NOTE: Current database ($CURRENT_DB_NAME) is not the target database ($TARGET_DB_NAME)"
            echo "The database initialization script will handle creating the target database"
        fi
    elif [ -n "$PGDATABASE" ] && [ -n "$PGHOST" ] && [ -n "$PGPORT" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then
        # If individual PG* variables are set but DATABASE_URL is not, construct it
        echo "Constructing DATABASE_URL from individual PG* variables"

        # Save the original database name
        ORIGINAL_PGDATABASE="$PGDATABASE"

        # Construct URL with the original database
        export DATABASE_URL="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
        echo "Constructed DATABASE_URL=$DATABASE_URL"

        # If the database name is not our target database, note this
        if [ "$PGDATABASE" != "$TARGET_DB_NAME" ]; then
            echo "NOTE: Current database ($PGDATABASE) is not the target database ($TARGET_DB_NAME)"
            echo "The database initialization script will handle creating the target database"
        fi
    elif [ -n "$DATABASE_PUBLIC_URL" ]; then
        echo "Using DATABASE_PUBLIC_URL as fallback"
        export DATABASE_URL="$DATABASE_PUBLIC_URL"

        # Get the current database name from the URL
        CURRENT_DB_NAME=$(echo $DATABASE_URL | awk -F/ '{print $NF}')
        echo "Current database name in URL: $CURRENT_DB_NAME"

        # If the database in the URL is not our target database, we'll need to create it
        if [ "$CURRENT_DB_NAME" != "$TARGET_DB_NAME" ]; then
            echo "NOTE: Current database ($CURRENT_DB_NAME) is not the target database ($TARGET_DB_NAME)"
            echo "The database initialization script will handle creating the target database"
        fi
    elif [[ "$DATABASE_URL" == *"postgres:admin@postgres"* ]]; then
        echo "ERROR: Found local development DATABASE_URL in production!"
        echo "Please remove the DATABASE_URL variable from Railway and link the PostgreSQL service's DATABASE_URL instead."
        exit 1
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
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER"; then
        break
    fi
    attempt=$((attempt+1))
    echo "Waiting for PostgreSQL to be ready... Attempt $attempt/$max_attempts"
    sleep 5
done

if [ $attempt -eq $max_attempts ]; then
    echo "ERROR: Could not connect to PostgreSQL after $max_attempts attempts"
    exit 1
fi

# Initialize database (this will create the target database if needed)
echo "Initializing database..."
python init_db.py

# The init_db.py script should have updated the DATABASE_URL environment variable
# to point to the target database, so we don't need to update it here

# Create pgvector extension
echo "Creating pgvector extension..."
psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT