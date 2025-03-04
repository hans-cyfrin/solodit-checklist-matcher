#!/bin/sh

echo "Initializing database..."
python init_db.py
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 "$@"