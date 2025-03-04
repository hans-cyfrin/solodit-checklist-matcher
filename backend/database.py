import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine with a longer timeout
engine = create_engine(
    DATABASE_URL,
    connect_args={"connect_timeout": 5}
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
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Create pgvector extension if it doesn't exist
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()

            # Create tables
            Base.metadata.create_all(bind=engine)
            print("Database initialized successfully")
            return
        except OperationalError as e:
            retry_count += 1
            if retry_count < max_retries:
                print(f"Database connection failed. Retrying in 2 seconds... ({retry_count}/{max_retries})")
                print(f"Error: {str(e)}")
                time.sleep(2)
            else:
                print("Failed to connect to the database after multiple attempts.")
                print("Please make sure the PostgreSQL database is running and accessible.")
                print(f"Error: {str(e)}")
                raise