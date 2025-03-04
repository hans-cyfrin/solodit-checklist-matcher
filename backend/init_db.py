import os
import time
import sys
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from models import Base
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
if os.getenv('RAILWAY_ENVIRONMENT') != 'production':
    load_dotenv()

# The desired database name for the application
TARGET_DB_NAME = 'solodit_checklist'

# Get database connection parameters from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("No DATABASE_URL found in environment variables!")
    # Check for individual connection parameters
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_host = os.getenv("PGHOST")
    pg_port = os.getenv("PGPORT", "5432")
    pg_database = os.getenv("PGDATABASE")

    if pg_user and pg_password and pg_host and pg_database:
        logger.info("Constructing DATABASE_URL from individual PG* variables")
        DATABASE_URL = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
    elif os.getenv("DATABASE_PUBLIC_URL"):
        logger.info("Using DATABASE_PUBLIC_URL as fallback")
        DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")
    else:
        logger.error("No valid database connection parameters found")
        sys.exit(1)

logger.info(f"Using DATABASE_URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0], '***SECRET***')}")

# Parse the DATABASE_URL to get connection parameters
try:
    result = urlparse(DATABASE_URL)
    DB_USER = result.username
    DB_PASSWORD = result.password
    DB_HOST = result.hostname
    DB_PORT = result.port or "5432"
    DB_NAME = result.path[1:] if result.path.startswith('/') else result.path

    logger.info(f"Parsed database connection parameters:")
    logger.info(f"DB_HOST: {DB_HOST}")
    logger.info(f"DB_PORT: {DB_PORT}")
    logger.info(f"DB_NAME: {DB_NAME}")
    logger.info(f"DB_USER: {DB_USER}")
except Exception as e:
    logger.error(f"Error parsing DATABASE_URL: {str(e)}")
    # Fallback to old parsing method
    try:
        db_params = DATABASE_URL.replace("postgresql://", "").split("/")
        db_connection = db_params[0].split("@")
        db_auth = db_connection[0].split(":")
        db_host = db_connection[1].split(":")

        DB_USER = db_auth[0]
        DB_PASSWORD = db_auth[1]
        DB_HOST = db_host[0]
        DB_PORT = db_host[1] if len(db_host) > 1 else "5432"
        DB_NAME = db_params[1]

        logger.info(f"Using fallback parsing for DATABASE_URL")
        logger.info(f"DB_HOST: {DB_HOST}")
        logger.info(f"DB_PORT: {DB_PORT}")
        logger.info(f"DB_NAME: {DB_NAME}")
        logger.info(f"DB_USER: {DB_USER}")
    except Exception as nested_e:
        logger.error(f"Error with fallback parsing of DATABASE_URL: {str(nested_e)}")
        sys.exit(1)

# Get or construct the admin connection URL (to the default/admin DB)
ADMIN_DB_URL = DATABASE_URL

# Construct a URL specifically for our target database
if DB_NAME != TARGET_DB_NAME:
    logger.info(f"Current database '{DB_NAME}' is not the target database '{TARGET_DB_NAME}'")
    # Create a URL for the target database by replacing the database name
    try:
        parts = DATABASE_URL.rsplit('/', 1)
        TARGET_DB_URL = f"{parts[0]}/{TARGET_DB_NAME}"
        logger.info(f"Target database URL: {TARGET_DB_URL.replace(TARGET_DB_URL.split('@')[0], '***SECRET***')}")
    except Exception as e:
        logger.error(f"Error constructing target database URL: {str(e)}")
        sys.exit(1)
else:
    TARGET_DB_URL = DATABASE_URL
    logger.info("Using the same database URL for admin and target")

def create_database():
    """Create the database if it doesn't exist"""
    # If we're already connected to the target database, no need to create it
    if DB_NAME == TARGET_DB_NAME:
        logger.info(f"Already connected to target database '{TARGET_DB_NAME}'")
        return True

    try:
        # Connect to PostgreSQL server using the admin/default database
        logger.info(f"Connecting to PostgreSQL server at {DB_HOST}:{DB_PORT}")
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,  # Connect to the existing database first
            connect_timeout=30
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if our target database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{TARGET_DB_NAME}'")
        exists = cursor.fetchone()

        if not exists:
            logger.info(f"Creating target database '{TARGET_DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}")
            logger.info(f"Target database '{TARGET_DB_NAME}' created successfully")

            # Update the DATABASE_URL environment variable to use the new database
            os.environ['DATABASE_URL'] = TARGET_DB_URL
            logger.info(f"Updated DATABASE_URL to: {TARGET_DB_URL.replace(TARGET_DB_URL.split('@')[0], '***SECRET***')}")
        else:
            logger.info(f"Target database '{TARGET_DB_NAME}' already exists")
            # Update the DATABASE_URL environment variable to use the existing target database
            os.environ['DATABASE_URL'] = TARGET_DB_URL
            logger.info(f"Updated DATABASE_URL to: {TARGET_DB_URL.replace(TARGET_DB_URL.split('@')[0], '***SECRET***')}")

        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error creating/checking database: {str(e)}")
        return False

def create_extension():
    """Create the pgvector extension"""
    try:
        # Connect to the target database
        logger.info(f"Connecting to target database '{TARGET_DB_NAME}' at {DB_HOST}:{DB_PORT}")
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=TARGET_DB_NAME,  # Connect to our target database
            connect_timeout=30
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create pgvector extension
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
        # Create SQLAlchemy engine - use the updated DATABASE_URL that points to our target database
        logger.info("Creating SQLAlchemy engine...")
        engine = create_engine(
            os.environ['DATABASE_URL'],  # This should now point to the target database
            connect_args={"connect_timeout": 60},
            pool_pre_ping=True
        )

        # Create tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)

        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Initializing database...")

    # Try to create database with retries
    max_retries = 8
    retry_count = 0
    retry_delay = 5

    while retry_count < max_retries:
        if create_database():
            break

        retry_count += 1
        if retry_count < max_retries:
            logger.info(f"Retrying in {retry_delay} seconds... ({retry_count}/{max_retries})")
            time.sleep(retry_delay)
        else:
            logger.error("Failed to create database after multiple attempts")
            exit(1)

    # Create pgvector extension
    extension_retries = 5
    extension_retry_count = 0

    while extension_retry_count < extension_retries:
        if create_extension():
            break

        extension_retry_count += 1
        if extension_retry_count < extension_retries:
            logger.info(f"Retrying extension creation in {retry_delay} seconds... ({extension_retry_count}/{extension_retries})")
            time.sleep(retry_delay)
        else:
            logger.error("Failed to create pgvector extension after multiple attempts")
            exit(1)

    # Create tables
    table_retries = 5
    table_retry_count = 0

    while table_retry_count < table_retries:
        if create_tables():
            break

        table_retry_count += 1
        if table_retry_count < table_retries:
            logger.info(f"Retrying table creation in {retry_delay} seconds... ({table_retry_count}/{table_retries})")
            time.sleep(retry_delay)
        else:
            logger.error("Failed to create tables after multiple attempts")
            exit(1)

    logger.info("Database initialization completed successfully")