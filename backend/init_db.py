import os
import time
import sys
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from models import Base
from urllib.parse import urlparse, urlunparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# The desired database name for the application
TARGET_DB_NAME = 'solodit_checklist'

# Get database connection parameters from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is required")
    sys.exit(1)

# Parse the DATABASE_URL to get connection parameters
try:
    result = urlparse(DATABASE_URL)
    DB_USER = result.username
    DB_PASSWORD = result.password
    DB_HOST = result.hostname
    DB_PORT = result.port or "5432"
    DB_NAME = result.path[1:] if result.path.startswith('/') else result.path

    # Construct URL for target database
    parts = urlparse(DATABASE_URL)
    target_parts = parts._replace(path=f"/{TARGET_DB_NAME}")
    TARGET_DB_URL = urlunparse(target_parts)
except Exception as e:
    logger.error(f"Error parsing DATABASE_URL: {str(e)}")
    sys.exit(1)

def attempt_connection(database, max_retries=3, retry_delay=2):
    """Attempt to connect to PostgreSQL with retries"""
    retry = 0
    last_error = None

    while retry < max_retries:
        try:
            logger.info(f"Attempting connection to database '{database}' (attempt {retry+1}/{max_retries})")
            # Use the DATABASE_URL directly but replace the database name
            db_url = DATABASE_URL.replace(DB_NAME, database)
            conn = psycopg2.connect(db_url)
            logger.info(f"Successfully connected to '{database}'")
            return conn
        except psycopg2.OperationalError as e:
            last_error = e
            error_msg = str(e).strip()
            logger.error(f"Connection failed: {error_msg}")
            retry += 1
            if retry < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

    if last_error:
        raise last_error
    return None

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # First try connecting to the target database directly
        try:
            conn = attempt_connection(TARGET_DB_NAME)
            if conn:
                logger.info(f"Target database '{TARGET_DB_NAME}' exists and is accessible")
                conn.close()
                os.environ['DATABASE_URL'] = TARGET_DB_URL
                return True
        except psycopg2.OperationalError as e:
            if "does not exist" not in str(e):
                raise e
            logger.info(f"Target database '{TARGET_DB_NAME}' does not exist. Will try to create it.")

        # Connect to postgres database to create the target database
        conn = attempt_connection('postgres', max_retries=5)
        if not conn:
            logger.error("Failed to connect to postgres database")
            return False

        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if target database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{TARGET_DB_NAME}'")
        exists = cursor.fetchone()

        if not exists:
            logger.info(f"Creating database '{TARGET_DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}")
            logger.info(f"Database '{TARGET_DB_NAME}' created successfully")
        else:
            logger.info(f"Database '{TARGET_DB_NAME}' already exists")

        cursor.close()
        conn.close()

        # Update DATABASE_URL to point to target database
        os.environ['DATABASE_URL'] = TARGET_DB_URL
        logger.info(f"Updated DATABASE_URL to point to target database")

        return True
    except Exception as e:
        logger.error(f"Error creating/checking database: {str(e)}")
        return False

def create_extension():
    """Create the pgvector extension"""
    try:
        conn = attempt_connection(TARGET_DB_NAME, max_retries=5)
        if not conn:
            logger.error("Failed to connect to target database for extension creation")
            return False

        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        logger.info("Creating pgvector extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

        cursor.close()
        conn.close()

        logger.info("pgvector extension created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating pgvector extension: {str(e)}")
        return False

def create_tables():
    """Create the database tables"""
    try:
        logger.info("Creating SQLAlchemy engine...")
        engine = create_engine(
            os.environ['DATABASE_URL'],
            connect_args={"connect_timeout": 60},
            pool_pre_ping=True,
            echo=True
        )

        logger.info("Testing database connection...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info(f"Connection test successful: {result.scalar()}")

        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Initializing database...")

    # Create database with retries
    max_retries = 5
    retry_count = 0
    retry_delay = 5

    while retry_count < max_retries:
        if create_database():
            break

        retry_count += 1
        if retry_count < max_retries:
            logger.info(f"Retrying database creation in {retry_delay} seconds... ({retry_count}/{max_retries})")
            time.sleep(retry_delay)
            retry_delay = min(30, retry_delay * 1.5)  # Increase delay with a cap
        else:
            logger.error("Failed to create database after multiple attempts")
            exit(1)

    # Create pgvector extension
    extension_retries = 3
    extension_retry_count = 0
    extension_retry_delay = 5

    while extension_retry_count < extension_retries:
        if create_extension():
            break

        extension_retry_count += 1
        if extension_retry_count < extension_retries:
            logger.info(f"Retrying extension creation in {extension_retry_delay} seconds... ({extension_retry_count}/{extension_retries})")
            time.sleep(extension_retry_delay)
            extension_retry_delay = min(30, extension_retry_delay * 1.5)
        else:
            logger.error("Failed to create pgvector extension after multiple attempts")
            logger.error("Will attempt to continue without pgvector extension")

    # Create tables
    table_retries = 3
    table_retry_count = 0
    table_retry_delay = 5

    while table_retry_count < table_retries:
        if create_tables():
            break

        table_retry_count += 1
        if table_retry_count < table_retries:
            logger.info(f"Retrying table creation in {table_retry_delay} seconds... ({table_retry_count}/{table_retries})")
            time.sleep(table_retry_delay)
            table_retry_delay = min(30, table_retry_delay * 1.5)
        else:
            logger.error("Failed to create tables after multiple attempts")
            exit(1)

    logger.info("Database initialization completed successfully")