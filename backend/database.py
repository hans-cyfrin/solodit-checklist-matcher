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

# Load environment variables without overriding existing ones
load_dotenv(override=False)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is required")
    sys.exit(1)

# Create SQLAlchemy engine
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"connect_timeout": 30},
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=True
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    sys.exit(1)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database with retries"""
    from models import Base
    max_retries = 5
    retry_count = 0
    retry_delay = 5

    while retry_count < max_retries:
        try:
            logger.info("Attempting to connect to database...")

            # Create pgvector extension
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
                retry_delay = min(30, retry_delay * 1.5)  # Increase delay with a cap
            else:
                logger.error("Failed to connect to the database after multiple attempts")
                logger.error("Please check if PostgreSQL is running and the connection URL is correct")
                raise