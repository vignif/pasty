import pytest
from fastapi.testclient import TestClient
import sqlite3
import re
import sys
import os

# Add project root to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
import db

client = TestClient(app)

@pytest.fixture(scope="function")
def tmp_db():
    """Setup in-memory DB for testing."""
    connection = db.get_connection(":memory:")  # Set the test connection
    db.initialize_db()  # Initialize the schema

    yield connection  # This is where the tests will run


# Test: Submit and retrieve content via web form
def test_submit_and_retrieve_via_web(tmp_db):
    text = "This is a test from web form."
    
    # Submit via HTML form
    response = client.post("/submit", data={"content": text})
    assert response.status_code == 200
    assert "Text Saved" in response.text or "ID:" in response.text

    # Extract ID from HTML response
    match = re.search(r"<strong>ID:</strong>\s*(\w+)", response.text)
    assert match is not None
    saved_id = match.group(1)

    # Retrieve via web form
    response = client.get(f"/retrieve?lookup_id={saved_id}")
    assert response.status_code == 200
    assert text in response.text

# Test: Save and get content via JSON API
def test_save_and_get_via_api(tmp_db):
    text = "This is a test from JSON API."
    
    # Save via JSON
    response = client.post("/save", json={"content": text})
    assert response.status_code == 200
    json_data = response.json()
    assert "id" in json_data
    saved_id = json_data["id"]

    # Get via JSON
    response = client.get(f"/get/{saved_id}")
    assert response.status_code == 200
    assert response.json()["content"] == text

# Test: 404 on invalid ID (both web form and API)
def test_404_on_invalid_id_web_and_api(tmp_db):
    fake_id = "invalid123"

    # API endpoint
    response = client.get(f"/get/{fake_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "ID not found"

    # Web form endpoint
    response = client.get(f"/retrieve?lookup_id={fake_id}")
    assert response.status_code == 200
    assert "ID not found" in response.text

# Test: Handle empty content submission
def test_empty_content_rejected_or_handled(tmp_db):
    # Web form submission with empty content
    response = client.post("/submit", data={"content": ""})
    assert response.status_code in [422, 200]  # Depending on how Form(...) is defined (required or not)

    # API submission with empty content
    response = client.post("/save", json={"content": ""})
    assert response.status_code == 200  # Allowed, but depends on your validation rules
    saved_id = response.json()["id"]
    assert isinstance(saved_id, str)

# Test: Multiple submissions generate unique IDs
def test_multiple_submissions_are_unique(tmp_db):
    contents = ["Alpha", "Beta", "Gamma"]
    ids = set()

    for content in contents:
        response = client.post("/save", json={"content": content})
        assert response.status_code == 200
        new_id = response.json()["id"]
        assert new_id not in ids
        ids.add(new_id)

        # Confirm content matches
        response = client.get(f"/get/{new_id}")
        assert response.status_code == 200
        assert response.json()["content"] == content

# Test: Simultaneous submissions (concurrent requests)
def test_simultaneous_submissions(tmp_db):
    """Test concurrent POST requests to check unique ID generation."""
    from concurrent.futures import ThreadPoolExecutor

    def submit_content(i):
        response = client.post("/save", json={"content": f"Sim test {i}"})
        assert response.status_code == 200
        return response.json()["id"]

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(submit_content, range(5)))

    assert len(set(results)) == 5  # All IDs should be unique

# Test: Check expired entries deletion (if applicable)
def test_delete_expired_entries(tmp_db):
    # Assuming delete_expired_entries is a method that deletes old records from the DB
    db.insert_text("test_id", "Some content", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z")
    
    # Call the method to delete expired entries
    db.delete_expired_entries()

    # Check that the entry is deleted (or doesn't exist anymore)
    row = db.get_text_by_id("test_id")
    assert row is None
