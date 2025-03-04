import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
logger.info(f"Connecting to database with URL: {DATABASE_URL}")

# Create SQLAlchemy engine with a longer timeout
engine = create_engine(
    DATABASE_URL,
    connect_args={"connect_timeout": 30}  # Increased timeout
)

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
    max_retries = 5  # Increased retries
    retry_count = 0
    retry_delay = 5  # Increased delay

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