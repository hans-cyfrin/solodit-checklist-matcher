#!/bin/bash

# Stop any running containers
echo "Stopping any running containers..."
docker-compose down

# Start containers with backend/.env file
echo "Starting containers with backend/.env..."
docker-compose --env-file ./backend/.env up -d

# Show container logs
echo -e "\nContainer logs:"
docker-compose logs -f