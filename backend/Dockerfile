FROM python:3.10-slim

WORKDIR /app

# Add PostgreSQL repository
RUN apt-get update && \
    apt-get install -y curl gnupg2 && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/postgresql.list

# Install system dependencies and PostgreSQL client
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client-15 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script first and make it executable
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--reload"]