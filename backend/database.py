import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables only in development
if os.getenv('RAILWAY_ENVIRONMENT') != 'production':
    load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# In Railway, check for various database connection options
if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not found, checking alternatives...")
        
        # Check if we have individual PostgreSQL connection parameters
        pg_user = os.getenv("PGUSER")
        pg_password = os.getenv("PGPASSWORD")
        pg_host = os.getenv("PGHOST")
        pg_port = os.getenv("PGPORT", "5432")
        pg_database = os.getenv("PGDATABASE")
        
        if pg_user and pg_password and pg_host and pg_database:
            logger.info("Constructing DATABASE_URL from individual PG* variables")
            DATABASE_URL = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        elif os.getenv("DATABASE_PUBLIC_URL"):
            logger.warning("Using DATABASE_PUBLIC_URL as fallback")
            DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")

# Validate DATABASE_URL
if not DATABASE_URL:
    logger.error("No DATABASE_URL found in environment variables!")
    sys.exit(1)

logger.info("Database configuration:")
logger.info(f"Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'development')}")
logger.info(f"DATABASE_URL format check: starts with postgresql:// = {DATABASE_URL.startswith('postgresql://')}")
logger.info(f"Using internal Railway connection: {'.railway.internal' in DATABASE_URL}")
try:
    db_host = DATABASE_URL.split('@')[1].split('/')[0]
    logger.info(f"Database host: {db_host}")
except IndexError:
    logger.error(f"Could not parse database host from DATABASE_URL: {DATABASE_URL}")

# Create SQLAlchemy engine with a longer timeout
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"connect_timeout": 60},  # Increased timeout
        pool_pre_ping=True,  # Enable connection validation
        pool_recycle=3600,   # Recycle connections after 1 hour
        echo=True            # Enable SQL query logging
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    sys.exit(1)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database
def init_db():
    from models import Base

    # Try to connect to the database
    max_retries = 8  # Increased retries
    retry_count = 0
    retry_delay = 10  # Increased delay

    while retry_count < max_retries:
        try:
            logger.info("Attempting to connect to database...")
            # Create pgvector extension if it doesn't exist
            with engine.connect() as conn:
                logger.info("Creating pgvector extension...")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()

            # Create tables
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully")
            return
        except OperationalError as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.error(f"Database connection failed. Retrying in {retry_delay} seconds... ({retry_count}/{max_retries})")
                logger.error(f"Error: {str(e)}")
                time.sleep(retry_delay)
            else:
                logger.error("Failed to connect to the database after multiple attempts.")
                logger.error("Please make sure the PostgreSQL database is running and accessible.")
                logger.error(f"Error: {str(e)}")
                raise