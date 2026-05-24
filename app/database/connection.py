import os
from sqlalchemy import create_engine
from sqlalchemy.orm import descriptive_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# We default to local sqlite database file 'music_platform.db'
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./music_platform.db")

# Create SQLAlchemy database engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Set up local session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for database models
Base = descriptive_base()

# Dependency to retrieve database session during API requests
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()