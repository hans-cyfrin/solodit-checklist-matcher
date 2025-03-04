import os
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from models import Base

# Load environment variables
load_dotenv()

# Get database connection parameters from environment
DATABASE_URL = os.getenv("DATABASE_URL")
db_params = DATABASE_URL.replace("postgresql://", "").split("/")
db_connection = db_params[0].split("@")
db_auth = db_connection[0].split(":")
db_host = db_connection[1].split(":")

DB_USER = db_auth[0]
DB_PASSWORD = db_auth[1]
DB_HOST = db_host[0]
DB_PORT = db_host[1] if len(db_host) > 1 else "5432"
DB_NAME = db_params[1]

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()

        if not exists:
            print(f"Creating database '{DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database '{DB_NAME}' created successfully")
        else:
            print(f"Database '{DB_NAME}' already exists")

        cursor.close()
        conn.close()

        return True
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        return False

def create_extension():
    """Create the pgvector extension"""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create pgvector extension
        print("Creating pgvector extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

        cursor.close()
        conn.close()

        print("pgvector extension created successfully")
        return True
    except Exception as e:
        print(f"Error creating pgvector extension: {str(e)}")
        return False

def create_tables():
    """Create the database tables"""
    try:
        # Create SQLAlchemy engine
        engine = create_engine(DATABASE_URL)

        # Create tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)

        print("Database tables created successfully")
        return True
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    print("Initializing database...")

    # Try to create database with retries
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        if create_database():
            break

        retry_count += 1
        if retry_count < max_retries:
            print(f"Retrying in 2 seconds... ({retry_count}/{max_retries})")
            time.sleep(2)
        else:
            print("Failed to create database after multiple attempts")
            exit(1)

    # Create pgvector extension
    if not create_extension():
        print("Failed to create pgvector extension")
        exit(1)

    # Create tables
    if not create_tables():
        print("Failed to create tables")
        exit(1)

    print("Database initialization completed successfully")