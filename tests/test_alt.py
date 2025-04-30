import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os 
import sys
# Add project root to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import initialize_db, insert_text, get_text_by_id, update_last_accessed, delete_expired_entries, generate_unique_id, id_exists, Text, Base

EXPIRATION_HOURS = int(os.getenv("EXPIRATION_HOURS", 24))

class TestTextStore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Use in-memory SQLite and set up tables
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.Session = sessionmaker(bind=cls.engine)

        # Patch engine and session in text_store module
        import db
        db.engine = cls.engine
        db.SessionLocal = cls.Session
        db.get_session = lambda: cls.Session()

        # Create tables
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cls.engine.dispose()
        Base.metadata.drop_all(cls.engine)

    def setUp(self):
        """Setup before each test method."""
        self.session = self.Session()

    def tearDown(self):
        """Clean up after each test method."""
        self.session.rollback()  # Rollback any changes made during a test
        self.session.close()

    def test_initialize_db(self):
        """Test the table creation."""
        # Ensure that the table is created
        #tables = self.session.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        from sqlalchemy import text
        tables = self.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='texts';")).fetchall()

        self.assertIn(('texts',), tables)

    def test_insert_text(self):
        """Test inserting a new text entry."""
        id_ = generate_unique_id()
        content = "Sample text"
        created_at = datetime.now(timezone.utc)
        last_accessed = created_at
        ip_address = "192.168.1.1"

        insert_text(id_, content, created_at, last_accessed, ip_address)

        # Query the inserted text
        text = self.session.query(Text).filter_by(id=id_).first()
        self.assertIsNotNone(text)
        self.assertEqual(text.content, content)

    def test_get_text_by_id(self):
        """Test retrieving a text by ID and incrementing retrieval count."""
        id_ = generate_unique_id()
        content = "Sample text"
        created_at = datetime.now(timezone.utc)
        last_accessed = created_at
        ip_address = "192.168.1.1"
        insert_text(id_, content, created_at, last_accessed, ip_address)

        # Retrieve the text and check the retrieval count
        retrieved_content = get_text_by_id(id_)
        self.assertEqual(retrieved_content, content)

        text = self.session.query(Text).filter_by(id=id_).first()
        self.assertEqual(text.retrieval_count, 1)


    def test_delete_expired_entries(self):
        """Test deleting expired entries based on the expiration cutoff."""
        id_ = generate_unique_id()
        content = "Sample text"
        created_at = datetime.now(timezone.utc) - timedelta(hours=EXPIRATION_HOURS + 1)  # Make it expired
        last_accessed = created_at
        ip_address = "192.168.1.1"
        insert_text(id_, content, created_at, last_accessed, ip_address)

        # Before deletion, check if the record exists
        text = self.session.query(Text).filter_by(id=id_).first()
        self.assertIsNotNone(text)

        delete_expired_entries()

        # After deletion, the record should be gone
        text = self.session.query(Text).filter_by(id=id_).first()
        self.assertIsNone(text)

    def test_generate_unique_id(self):
        """Test generating unique IDs."""
        id_1 = generate_unique_id()
        id_2 = generate_unique_id()
        self.assertNotEqual(id_1, id_2)
        self.assertEqual(len(id_1), 4)
        self.assertEqual(len(id_2), 4)

    def test_id_exists(self):
        """Test checking if an ID exists in the database."""
        id_ = generate_unique_id()
        content = "Sample text"
        created_at = datetime.now(timezone.utc)
        last_accessed = created_at
        ip_address = "192.168.1.1"
        insert_text(id_, content, created_at, last_accessed, ip_address)

        # Check if the ID exists
        self.assertTrue(id_exists(id_))

        # Check for a non-existent ID
        self.assertFalse(id_exists("NONEXISTENT"))

if __name__ == '__main__':
    unittest.main()
