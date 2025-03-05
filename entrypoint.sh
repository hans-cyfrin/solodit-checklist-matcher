#!/bin/bash

# Target database name
TARGET_DB_NAME="solodit_checklist"

# Debug: Print all environment variables
echo "DEBUG: All environment variables:"
env | sort

echo "DEBUG: Current DATABASE_URL=$DATABASE_URL"
echo "DEBUG: Current DATABASE_PUBLIC_URL=$DATABASE_PUBLIC_URL"

# FIRST PRIORITY: Use Railway's public URL if available
# Since we know the public URL works, we'll use it first
if [ -n "$DATABASE_PUBLIC_URL" ]; then
    echo "Using DATABASE_PUBLIC_URL for connection as it's known to work"
    export DATABASE_URL="$DATABASE_PUBLIC_URL"
    echo "Set DATABASE_URL=$DATABASE_URL"
elif [ -z "$DATABASE_URL" ] && [ -n "$PGDATABASE" ] && [ -n "$PGHOST" ] && [ -n "$PGPORT" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then
    # Construct DATABASE_URL from individual PG* variables
    echo "Constructing DATABASE_URL from individual PG* variables"
    export DATABASE_URL="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
    echo "Constructed DATABASE_URL=$DATABASE_URL"
fi

# If we're in Railway and DATABASE_URL contains railway.internal but we have public access info,
# let's use the public access info
if [ "$RAILWAY_ENVIRONMENT" = "production" ] && [[ "$DATABASE_URL" == *"railway.internal"* ]]; then
    echo "WARNING: Using internal Railway URL. This might cause connection issues."

    # If we have the public proxy info from the user, construct a URL
    if [ -n "$PUBLIC_DB_HOST" ] && [ -n "$PUBLIC_DB_PORT" ]; then
        echo "Public database connection info available, using it instead"
        PUBLIC_URL="postgresql://$PGUSER:$PGPASSWORD@$PUBLIC_DB_HOST:$PUBLIC_DB_PORT/$PGDATABASE"
        echo "Using public connection: $PUBLIC_URL (with password masked)"
        export DATABASE_URL="$PUBLIC_URL"
    fi
fi

# Validate DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: No valid PostgreSQL URL found!"
    echo "Please make sure to add a PostgreSQL service in Railway and link its connection variables"
    exit 1
fi

echo "DEBUG: Final DATABASE_URL=$DATABASE_URL"

# Parse DATABASE_URL to extract connection details
if [ -n "$DATABASE_URL" ]; then
    # Extract connection details from DATABASE_URL
    PGUSER=$(echo $DATABASE_URL | awk -F[:/@] '{print $4}')
    PGPASSWORD=$(echo $DATABASE_URL | awk -F[:/@] '{print $5}')
    PGHOST=$(echo $DATABASE_URL | awk -F[:/@] '{print $6}')
    PGPORT=$(echo $DATABASE_URL | awk -F[:/@] '{print $7}' | awk -F/ '{print $1}')
    PGDATABASE=$(echo $DATABASE_URL | awk -F/ '{print $NF}')

    # Export for use by other commands
    export PGUSER PGPASSWORD PGHOST PGPORT PGDATABASE

    echo "DEBUG: Parsed database connection details:"
    echo "PGHOST=$PGHOST"
    echo "PGPORT=$PGPORT"
    echo "PGUSER=$PGUSER"
    echo "PGDATABASE=$PGDATABASE"
else
    echo "ERROR: Failed to parse DATABASE_URL!"
    exit 1
fi

# Networking diagnostics for Railway
echo "Performing network diagnostics..."
echo "Checking DNS resolution..."
# Check if host command is available
if command -v host >/dev/null 2>&1; then
    host $PGHOST || echo "WARNING: Unable to resolve hostname $PGHOST"
else
    echo "Host command not available. Skipping DNS check."
fi

# Try ping if available (unlikely to work in most container environments)
if command -v ping >/dev/null 2>&1; then
    echo "Attempting ping to database host..."
    ping -c 1 $PGHOST || echo "WARNING: Unable to ping $PGHOST (this is normal in some container environments)"
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
echo "Trying to connect to PostgreSQL at $PGHOST:$PGPORT..."

# Use a more reliable approach with a timeout
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    # Try using PGPASSWORD with psql directly - more reliable than pg_isready in some cases
    PGPASSWORD=$PGPASSWORD psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "postgres" -c "SELECT 1;" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Successfully connected to PostgreSQL!"
        break
    fi

    # Fallback to pg_isready
    if pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -t 5; then
        echo "PostgreSQL is ready according to pg_isready."
        break
    fi

    attempt=$((attempt+1))
    echo "Waiting for PostgreSQL to be ready... Attempt $attempt/$max_attempts"
    sleep 5
done

if [ $attempt -eq $max_attempts ]; then
    echo "ERROR: Could not connect to PostgreSQL after $max_attempts attempts"
    echo "Final connection info being used:"
    echo "Host: $PGHOST"
    echo "Port: $PGPORT"
    echo "User: $PGUSER"
    echo "Database: $PGDATABASE"

    # If the host is still railway.internal, we need to tell the user to use the public URL
    if [[ "$PGHOST" == *"railway.internal"* ]]; then
        echo ""
        echo "================ CRITICAL RAILWAY CONNECTION ERROR ================"
        echo "You are trying to use Railway's internal networking which is failing."
        echo "Please add the following environment variables to your Railway project:"
        echo ""
        echo "PUBLIC_DB_HOST=mainline.proxy.rlwy.net"
        echo "PUBLIC_DB_PORT=31284"
        echo ""
        echo "These values should match the connection you confirmed works locally:"
        echo "PGPASSWORD=*** psql -h mainline.proxy.rlwy.net -U postgres -p 31284 -d railway"
        echo "=================================================================="
    fi

    exit 1
fi

# Initialize database (this will create the target database if needed)
echo "Initializing database..."
python init_db.py || {
    echo "ERROR: Database initialization failed!"
    exit 1
}

# Create pgvector extension
echo "Creating pgvector extension..."
PGPASSWORD=$PGPASSWORD psql "$DATABASE_URL" -c 'CREATE EXTENSION IF NOT EXISTS vector;' || {
    echo "WARNING: Failed to create pgvector extension. Will try to continue anyway."
}

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}