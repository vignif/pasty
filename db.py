
"""
db.py

Database layer for Pasty. Handles text storage, retrieval, expiration, and unique ID generation using SQLAlchemy and SQLite.
"""

from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import random
import string
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Constants
EXPIRATION_HOURS = int(os.getenv("EXPIRATION_HOURS", 24))
db_url = os.getenv("DATABASE_URL", "sqlite:///text_store.db")  # Use SQLAlchemy URI format

# SQLAlchemy setup
Base = declarative_base()

engine = create_engine(db_url, connect_args={"check_same_thread": False} if 'sqlite' in db_url else {})
Session = sessionmaker(bind=engine)
current_session = None

# Define Text model

class Text(Base):
    """SQLAlchemy model for text entries."""
    __tablename__ = 'texts'

    id = Column(String(4), primary_key=True)
    content = Column(String)
    created_at = Column(DateTime, default=func.now())
    last_accessed = Column(DateTime)
    ip_address = Column(String)
    retrieval_count = Column(Integer, default=0)

# Set connection/session for global use

def set_session(session):
    """Set the global database session."""
    global current_session
    current_session = session


@contextmanager
def get_session():
    """Context manager for database session handling."""
    global current_session
    if current_session:
        yield current_session
    else:
        session = Session()
        try:
            yield session
        finally:
            session.close()

def initialize_db():
    """Create the table if it doesn't exist."""
    Base.metadata.create_all(engine)

def generate_unique_id():
    """Generate a unique 4-character ID using only uppercase letters."""
    while True:
        id_ = "".join(random.choices(string.ascii_uppercase, k=4))
        if not id_exists(id_):
            return id_

def insert_text(id_, content, created_at, last_accessed, ip_address):
    """Insert a new text entry into the database."""
    with get_session() as session:
        text = Text(id=id_, content=content, created_at=created_at, last_accessed=last_accessed, ip_address=ip_address)
        session.add(text)
        session.commit()

def get_text_by_id(id_):
    """Retrieve text content by ID and increment retrieval count."""
    with get_session() as session:
        text = session.query(Text).filter_by(id=id_).first()
        if text:
            text.retrieval_count += 1
            session.commit()
            return text.content
        return None

def update_last_accessed(id_, timestamp):
    """Update the last accessed timestamp for a text entry."""
    with get_session() as session:
        text = session.query(Text).filter_by(id=id_).first()
        if text:
            text.last_accessed = timestamp
            session.commit()

def delete_expired_entries():
    """Delete expired entries based on the expiration cutoff."""
    with get_session() as session:
        expiry_cutoff = datetime.now(timezone.utc) - timedelta(hours=EXPIRATION_HOURS)
        session.query(Text).filter(Text.created_at < expiry_cutoff).delete()
        session.commit()

def id_exists(id_):
    """Check if a text entry with the given ID exists."""
    with get_session() as session:
        return session.query(Text.id).filter_by(id=id_).first() is not None


def get_db_count():
    with get_session() as session:
        return session.query(Text).count()