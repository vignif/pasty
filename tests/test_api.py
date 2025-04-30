import pytest
from fastapi.testclient import TestClient
import os 
import sys
# Add project root to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app  # adjust this if your app is in a different file
from unittest.mock import patch

client = TestClient(app)

# @patch("db.get_db_count", return_value=42)
# def test_get_count(mock_count):
#     response = client.get("/api/count")
#     assert response.status_code == 200
#     assert response.json() == {"count": 42}
#     mock_count.assert_called_once()

# @patch("db.generate_unique_id", return_value="abc123")
# @patch("db.insert_text")
# def test_api_save(mock_insert, mock_generate_id):
#     response = client.post("/save", json={"content": "Hello world!"})
#     assert response.status_code == 200
#     assert response.json() == {"id": "abc123"}
#     mock_insert.assert_called_once()

# @patch("db.delete_expired_entries")
# @patch("db.get_text_by_id", return_value=("This is the content",))
# @patch("db.update_last_accessed")
# def test_api_get_success(mock_update, mock_get, mock_delete):
#     response = client.get("/get/test123")
#     assert response.status_code == 200
#     assert response.json() == {"content": "This is the content"}
#     mock_get.assert_called_once_with("test123")
#     mock_update.assert_called_once()

# @patch("db.delete_expired_entries")
# @patch("db.get_text_by_id", return_value=None)
# def test_api_get_not_found(mock_get, mock_delete):
#     response = client.get("/get/unknown")
#     assert response.status_code == 404
#     assert response.json() == {"detail": "ID not found"}
#     mock_get.assert_called_once_with("unknown")
