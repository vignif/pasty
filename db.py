import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import random
import string

load_dotenv()

EXPIRATION_HOURS = int(os.getenv("EXPIRATION_HOURS", 72))

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///store.db')


# This will hold the thread-local connection for each thread
thread_local = threading.local()

def set_connection(connection):
    """Set the current DB connection to the provided one (used for testing)."""
    thread_local.connection = connection

@contextmanager
def get_connection():
    """Get the current DB connection, ensuring thread safety using thread-local storage."""
    if hasattr(thread_local, 'connection'):
        yield thread_local.connection
    else:
        # If no thread-local connection exists, create one for this thread
        conn = sqlite3.connect(DATABASE_URL, check_same_thread=False)
        thread_local.connection = conn
        try:
            yield conn
        finally:
            conn.close()
            del thread_local.connection  # Clear thread-local connection after use

# Create the table if it doesn't exist
def initialize_db():
    """Initialize the database by creating the necessary tables."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS texts (
                id TEXT PRIMARY KEY,
                content TEXT,
                created_at TEXT,
                last_accessed TEXT
            )
        """)
        connection.commit()

initialize_db()  # Ensure table is created on startup

def generate_unique_id():
    """Generate a unique 4-character ID for new entries."""
    while True:
        id_ = "".join(random.choices(string.ascii_letters, k=4))
        if not id_exists(id_):
            return id_

def insert_text(id_, content, created_at, last_accessed):
    """Insert a new text entry into the database."""
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO texts (id, content, created_at, last_accessed) VALUES (?, ?, ?, ?)",
            (id_, content, created_at, last_accessed)
        )
        connection.commit()

def get_text_by_id(id_):
    """Retrieve text content by ID."""
    with get_connection() as connection:
        cur = connection.execute("SELECT content FROM texts WHERE id = ?", (id_,))
        return cur.fetchone()

def update_last_accessed(id_, timestamp):
    """Update the last accessed timestamp for a given ID."""
    with get_connection() as connection:
        connection.execute("UPDATE texts SET last_accessed = ? WHERE id = ?", (timestamp, id_))
        connection.commit()

def delete_expired_entries():
    """Delete entries that are older than the specified expiration time."""
    with get_connection() as connection:
        expiry_cutoff = datetime.now(timezone.utc) - timedelta(hours=EXPIRATION_HOURS)
        connection.execute("DELETE FROM texts WHERE created_at < ?", (expiry_cutoff.isoformat(),))
        connection.commit()

def id_exists(id_):
    """Check if a text entry with the given ID already exists."""
    with get_connection() as connection:
        cur = connection.execute("SELECT 1 FROM texts WHERE id = ?", (id_,))
        return cur.fetchone() is not None
