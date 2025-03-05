import os
import time
import sys
import logging
import socket
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

# Mask password for logging
masked_url = DATABASE_URL
try:
    parts = urlparse(DATABASE_URL)
    netloc = parts.netloc
    if '@' in netloc:
        userpass, hostport = netloc.split('@', 1)
        if ':' in userpass:
            user, _ = userpass.split(':', 1)
            masked_netloc = f"{user}:****@{hostport}"
            masked_parts = parts._replace(netloc=masked_netloc)
            masked_url = urlunparse(masked_parts)
except Exception:
    masked_url = "****"  # Fallback if parsing fails

logger.info(f"Using DATABASE_URL: {masked_url}")

# Perform Railway-specific network diagnostics
def perform_network_diagnostics(host, port):
    """Perform basic network diagnostics on the database host"""
    logger.info(f"Performing network diagnostics for {host}:{port}")

    # Try to resolve hostname
    try:
        logger.info(f"Resolving hostname {host}...")
        ip_address = socket.gethostbyname(host)
        logger.info(f"Hostname {host} resolved to {ip_address}")
    except socket.gaierror as e:
        logger.error(f"Failed to resolve hostname {host}: {e}")
        if "railway.internal" in host:
            logger.error("This appears to be a Railway internal DNS issue.")
            logger.error("Please ensure the PostgreSQL service is properly linked.")

    # Try to connect to the port
    try:
        logger.info(f"Testing connection to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(port)))
        if result == 0:
            logger.info(f"Port {port} is open on {host}")
        else:
            logger.error(f"Port {port} is closed on {host}")
            if "railway.internal" in host:
                logger.error("This indicates a Railway networking issue between services.")
        sock.close()
    except Exception as e:
        logger.error(f"Socket connection test failed: {e}")

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

    # Run diagnostics in Railway environment
    if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
        perform_network_diagnostics(DB_HOST, DB_PORT)
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

        # Run diagnostics in Railway environment with fallback parsing
        if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
            perform_network_diagnostics(DB_HOST, DB_PORT)
    except Exception as nested_e:
        logger.error(f"Error with fallback parsing of DATABASE_URL: {str(nested_e)}")
        sys.exit(1)

# Get or construct the admin connection URL (to the default/admin DB)
ADMIN_DB_URL = DATABASE_URL

# For Railway, try to use the 'postgres' database as admin database for more reliable connections
if "railway.internal" in DB_HOST and DB_NAME != "postgres":
    try:
        parts = urlparse(DATABASE_URL)
        path = "/postgres"  # Try to connect to the postgres database first
        admin_parts = parts._replace(path=path)
        ADMIN_DB_URL = urlunparse(admin_parts)
        logger.info(f"Using 'postgres' database for admin connection on Railway")
    except Exception as e:
        logger.error(f"Failed to construct admin URL: {e}")
        # Keep using the original URL

# Construct a URL specifically for our target database
try:
    parts = urlparse(DATABASE_URL)
    path = f"/{TARGET_DB_NAME}"
    target_parts = parts._replace(path=path)
    TARGET_DB_URL = urlunparse(target_parts)

    # Mask password for logging
    masked_parts = urlparse(TARGET_DB_URL)
    netloc = masked_parts.netloc
    if '@' in netloc:
        userpass, hostport = netloc.split('@', 1)
        if ':' in userpass:
            user, _ = userpass.split(':', 1)
            masked_netloc = f"{user}:****@{hostport}"
            masked_parts = masked_parts._replace(netloc=masked_netloc)
            masked_target_url = urlunparse(masked_parts)
            logger.info(f"Target database URL: {masked_target_url}")
except Exception as e:
    logger.error(f"Error constructing target database URL: {str(e)}")
    TARGET_DB_URL = DATABASE_URL
    logger.info("Using original DATABASE_URL as target")

def attempt_connection(host, port, user, password, database, max_retries=3, retry_delay=2):
    """Attempt to connect to PostgreSQL with retries"""
    retry = 0
    last_error = None

    while retry < max_retries:
        try:
            logger.info(f"Attempting connection to {database} at {host}:{port} (attempt {retry+1}/{max_retries})")
            conn = psycopg2.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                database=database,
                connect_timeout=10
            )
            logger.info(f"Successfully connected to {database}")
            return conn
        except psycopg2.OperationalError as e:
            last_error = e
            error_msg = str(e).strip()
            logger.error(f"Connection failed: {error_msg}")

            # Special case for Railway internal connections
            if "railway.internal" in host:
                if "could not translate host" in error_msg or "could not connect to server" in error_msg:
                    logger.error("This appears to be a Railway networking issue.")
                    logger.error("Please verify your Railway configuration and service links.")

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
        logger.info(f"Trying to connect directly to target database '{TARGET_DB_NAME}'...")
        try:
            conn = attempt_connection(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=TARGET_DB_NAME
            )
            if conn:
                logger.info(f"Target database '{TARGET_DB_NAME}' exists and is accessible")
                conn.close()

                # Update the DATABASE_URL environment variable to use the target database
                os.environ['DATABASE_URL'] = TARGET_DB_URL
                return True
        except psycopg2.OperationalError as e:
            if "does not exist" in str(e):
                logger.info(f"Target database '{TARGET_DB_NAME}' does not exist. Will try to create it.")
            else:
                # Some other connection error
                logger.error(f"Error connecting to target database: {str(e)}")

        # Connect to admin database to create the target database
        logger.info(f"Connecting to admin database to create target database...")
        conn = attempt_connection(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,  # Use original database from URL
            max_retries=5
        )

        if not conn:
            logger.error("Failed to connect to admin database after retries")
            return False

        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if our target database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{TARGET_DB_NAME}'")
        exists = cursor.fetchone()

        if not exists:
            logger.info(f"Creating target database '{TARGET_DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {TARGET_DB_NAME}")
            logger.info(f"Target database '{TARGET_DB_NAME}' created successfully")
        else:
            logger.info(f"Target database '{TARGET_DB_NAME}' already exists")

        cursor.close()
        conn.close()

        # Update the DATABASE_URL environment variable to use the target database
        os.environ['DATABASE_URL'] = TARGET_DB_URL
        logger.info(f"Updated DATABASE_URL to point to target database")

        return True
    except Exception as e:
        logger.error(f"Error creating/checking database: {str(e)}")
        return False

def create_extension():
    """Create the pgvector extension"""
    try:
        # Connect to the target database
        logger.info(f"Connecting to target database '{TARGET_DB_NAME}' for extension creation...")
        conn = attempt_connection(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=TARGET_DB_NAME,
            max_retries=5
        )

        if not conn:
            logger.error("Failed to connect to target database for extension creation")
            return False

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
            os.environ['DATABASE_URL'],
            connect_args={"connect_timeout": 60},
            pool_pre_ping=True,
            echo=True
        )

        # Verify connection
        logger.info("Testing SQLAlchemy engine connection...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info(f"SQLAlchemy connection test result: {result.scalar()}")

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
            logger.info(f"Retrying database creation in {retry_delay} seconds... ({retry_count}/{max_retries})")
            time.sleep(retry_delay)
            retry_delay = min(30, retry_delay * 1.5)  # Increase delay with a cap
        else:
            logger.error("Failed to create database after multiple attempts")
            if "railway.internal" in DB_HOST:
                logger.error("This is likely a Railway networking issue.")
                logger.error("Please verify that your PostgreSQL service is correctly linked.")
                logger.error("You may need to recreate the link between your app and PostgreSQL.")
            exit(1)

    # Create pgvector extension
    extension_retries = 5
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
    table_retries = 5
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