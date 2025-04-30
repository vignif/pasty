import sqlite3
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import random
import string
from contextlib import contextmanager

load_dotenv()

# Constants
EXPIRATION_HOURS = int(os.getenv("EXPIRATION_HOURS", 24))
# Determine database location
db_url = os.getenv("DATABASE_URL", "text_store.db")

# This will hold the current connection for testing
current_connection = None

def set_connection(connection):
    """Set the current DB connection to the provided one (used for testing)."""
    global current_connection
    current_connection = connection

@contextmanager
def get_connection(db_url=db_url):
    """Get a connection to the database."""
    if current_connection:
        yield current_connection
    else:
        conn = sqlite3.connect(db_url, check_same_thread=False)
        try:
            yield conn
        finally:
            conn.close()

def initialize_db():
    """Create the table if it doesn't exist."""
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


def generate_unique_id():
    """Generate a unique 4-character ID using only uppercase letters."""
    while True:
        id_ = "".join(random.choices(string.ascii_uppercase, k=4))
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
