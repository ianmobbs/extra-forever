"""
Tests for app/controllers/messages_controller.py
"""
import json
import base64
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.controllers.messages_controller import (
    MessagesController,
    MessageResponse,
    ImportResponse
)
from app.services.messages_service import ImportOptions, ImportResult
from models import Message


class TestMessageResponse:
    """Test MessageResponse Pydantic model."""
    
    def test_message_response_creation(self):
        """Test creating a MessageResponse."""
        response = MessageResponse(
            id="test123",
            subject="Test Subject",
            sender="test@example.com",
            snippet="Test snippet"
        )
        assert response.id == "test123"
        assert response.subject == "Test Subject"
    
    def test_message_response_optional_snippet(self):
        """Test MessageResponse with None snippet."""
        response = MessageResponse(
            id="test123",
            subject="Test Subject",
            sender="test@example.com",
            snippet=None
        )
        assert response.snippet is None


class TestImportResponse:
    """Test ImportResponse Pydantic model."""
    
    def test_import_response_creation(self):
        """Test creating an ImportResponse."""
        preview = [
            MessageResponse(
                id="msg1",
                subject="Subject 1",
                sender="sender@example.com",
                snippet="snippet"
            )
        ]
        response = ImportResponse(total_imported=5, preview=preview)
        assert response.total_imported == 5
        assert len(response.preview) == 1


class TestMessagesController:
    """Test MessagesController class."""
    
    def test_controller_initialization(self, temp_db):
        """Test controller can be initialized."""
        controller = MessagesController(db_path=temp_db)
        assert controller.store is not None
        assert controller.router is not None
    
    def test_controller_has_routes(self, temp_db):
        """Test controller registers routes."""
        controller = MessagesController(db_path=temp_db)
        routes = [route.path for route in controller.router.routes]
        assert "/messages/import" in routes
    
    def test_import_messages(self, temp_db, sample_jsonl_file):
        """Test import_messages method."""
        controller = MessagesController(db_path=temp_db)
        options = ImportOptions(drop_existing=True)
        
        result = controller.import_messages(sample_jsonl_file, options)
        
        assert isinstance(result, ImportResult)
        assert result.total_imported == 3
        assert len(result.preview_messages) == 3
    
    def test_import_messages_with_options(self, temp_db, sample_jsonl_file):
        """Test import_messages respects drop_existing option."""
        controller = MessagesController(db_path=temp_db)
        
        # First import with drop
        options1 = ImportOptions(drop_existing=True)
        result1 = controller.import_messages(sample_jsonl_file, options1)
        assert result1.total_imported == 3
        
        session = controller.store.create_session()
        count = session.query(Message).count()
        assert count == 3
        session.close()
        
        # Second import with drop should replace
        options2 = ImportOptions(drop_existing=True)
        result2 = controller.import_messages(sample_jsonl_file, options2)
        assert result2.total_imported == 3
        
        # Should still be 3 (replaced, not added)
        session = controller.store.create_session()
        count = session.query(Message).count()
        assert count == 3
        session.close()


class TestMessagesControllerAPI:
    """Test MessagesController API endpoints."""
    
    @pytest.fixture
    def client(self, temp_db):
        """Create a test client with the controller router."""
        from fastapi import FastAPI
        controller = MessagesController(db_path=temp_db)
        app = FastAPI()
        app.include_router(controller.router)
        return TestClient(app)
    
    def test_import_upload_endpoint(self, client, sample_jsonl_file):
        """Test /import endpoint with file upload."""
        with open(sample_jsonl_file, 'rb') as f:
            response = client.post(
                "/messages/import",
                files={"file": ("messages.jsonl", f, "application/jsonl")},
                data={"drop_existing": "true"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_imported"] == 3
        assert len(data["preview"]) == 3
    
    def test_import_upload_preserves_data(self, client, sample_jsonl_file):
        """Test that imported data is preserved correctly."""
        with open(sample_jsonl_file, 'rb') as f:
            response = client.post(
                "/messages/import",
                files={"file": ("messages.jsonl", f, "application/jsonl")},
                data={"drop_existing": "true"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check first message
        first_msg = data["preview"][0]
        assert first_msg["id"] == "msg1"
        assert first_msg["subject"] == "Test Email 1"
        assert first_msg["sender"] == "Sender One <sender1@example.com>"
        assert first_msg["snippet"] == "First test"
    
    def test_import_upload_without_drop(self, client, tmp_path):
        """Test import without dropping existing data."""
        # Create two files
        file1 = tmp_path / "file1.jsonl"
        file2 = tmp_path / "file2.jsonl"
        
        msg1 = {
            "id": "msg1",
            "subject": "First",
            "from": "test@example.com",
            "to": ["recipient@example.com"],
            "snippet": "snippet",
            "body": base64.b64encode(b"body").decode('utf-8'),
            "date": "2025-01-01T12:00:00Z"
        }
        
        with open(file1, 'w') as f:
            f.write(json.dumps(msg1) + '\n')
        
        msg2 = {
            "id": "msg2",
            "subject": "Second",
            "from": "test@example.com",
            "to": ["recipient@example.com"],
            "snippet": "snippet",
            "body": base64.b64encode(b"body").decode('utf-8'),
            "date": "2025-01-02T12:00:00Z"
        }
        
        with open(file2, 'w') as f:
            f.write(json.dumps(msg2) + '\n')
        
        # First upload with drop
        with open(file1, 'rb') as f:
            response1 = client.post(
                "/messages/import",
                files={"file": ("file1.jsonl", f, "application/jsonl")},
                data={"drop_existing": "true"}
            )
        assert response1.status_code == 200
        
        # Second upload without drop
        with open(file2, 'rb') as f:
            response2 = client.post(
                "/messages/import",
                files={"file": ("file2.jsonl", f, "application/jsonl")},
                data={"drop_existing": "false"}
            )
        assert response2.status_code == 200


class TestMessagesControllerIntegration:
    """Integration tests for MessagesController."""
    
    def test_full_import_workflow(self, temp_db, tmp_path):
        """
        Integration test: Complete import workflow.
        Tests the full flow from file creation to data retrieval.
        """
        # Create controller
        controller = MessagesController(db_path=temp_db)
        
        # Create test data
        messages = [
            {
                "id": f"msg{i}",
                "subject": f"Subject {i}",
                "from": f"Sender {i} <sender{i}@example.com>",
                "to": ["recipient@example.com"],
                "snippet": f"Snippet {i}",
                "body": base64.b64encode(f"Body {i}".encode()).decode('utf-8'),
                "date": f"2025-01-0{i+1}T12:00:00Z"
            }
            for i in range(5)
        ]
        
        file_path = tmp_path / "integration_test.jsonl"
        with open(file_path, 'w') as f:
            for msg in messages:
                f.write(json.dumps(msg) + '\n')
        
        # Import messages
        options = ImportOptions(drop_existing=True)
        result = controller.import_messages(file_path, options)
        
        # Verify import result
        assert result.total_imported == 5
        assert len(result.preview_messages) == 5
        
        # Verify data in database
        session = controller.store.create_session()
        db_messages = session.query(Message).all()
        assert len(db_messages) == 5
        
        # Verify fields are correct
        msg = db_messages[0]
        assert msg.id == "msg0"
        assert msg.subject == "Subject 0"
        assert "sender0@example.com" in msg.sender
        
        session.close()
    
    def test_api_to_database_integration(self, temp_db, sample_jsonl_file):
        """
        Integration test: API upload persists to database.
        Tests the full API flow from upload to database storage.
        """
        from fastapi import FastAPI
        
        controller = MessagesController(db_path=temp_db)
        app = FastAPI()
        app.include_router(controller.router)
        client = TestClient(app)
        
        # Upload via API
        with open(sample_jsonl_file, 'rb') as f:
            response = client.post(
                "/messages/import",
                files={"file": ("messages.jsonl", f, "application/jsonl")},
                data={"drop_existing": "true"}
            )
        
        assert response.status_code == 200
        api_data = response.json()
        
        # Verify data in database
        session = controller.store.create_session()
        db_messages = session.query(Message).all()
        assert len(db_messages) == api_data["total_imported"]
        
        # Verify API preview matches database
        for api_msg, db_msg in zip(api_data["preview"], db_messages):
            assert api_msg["id"] == db_msg.id
            assert api_msg["subject"] == db_msg.subject
            assert api_msg["sender"] == db_msg.sender
        
        session.close()
    
    def test_multiple_imports_with_drop(self, temp_db, sample_jsonl_file):
        """
        Integration test: Multiple imports with drop_existing.
        Tests that data is properly replaced on subsequent imports.
        """
        controller = MessagesController(db_path=temp_db)
        
        # First import
        options = ImportOptions(drop_existing=True)
        result1 = controller.import_messages(sample_jsonl_file, options)
        assert result1.total_imported == 3
        
        # Second import (should replace)
        result2 = controller.import_messages(sample_jsonl_file, options)
        assert result2.total_imported == 3
        
        # Verify only 3 messages in database (not 6)
        session = controller.store.create_session()
        count = session.query(Message).count()
        assert count == 3
        session.close()
    
    def test_cli_and_api_use_same_data(self, temp_db, tmp_path):
        """
        Integration test: CLI and API access same data.
        Tests that both interfaces work with the same underlying data.
        """
        from fastapi import FastAPI
        
        # Create two different files with different message IDs
        file1 = tmp_path / "cli_messages.jsonl"
        file2 = tmp_path / "api_messages.jsonl"
        
        import base64
        cli_msgs = [
            {
                "id": f"cli_msg{i}",
                "subject": f"CLI Subject {i}",
                "from": "test@example.com",
                "to": ["recipient@example.com"],
                "snippet": "snippet",
                "body": base64.b64encode(b"body").decode('utf-8'),
                "date": "2025-01-01T12:00:00Z"
            }
            for i in range(2)
        ]
        
        api_msgs = [
            {
                "id": f"api_msg{i}",
                "subject": f"API Subject {i}",
                "from": "test@example.com",
                "to": ["recipient@example.com"],
                "snippet": "snippet",
                "body": base64.b64encode(b"body").decode('utf-8'),
                "date": "2025-01-02T12:00:00Z"
            }
            for i in range(2)
        ]
        
        with open(file1, 'w') as f:
            for msg in cli_msgs:
                f.write(json.dumps(msg) + '\n')
        
        with open(file2, 'w') as f:
            for msg in api_msgs:
                f.write(json.dumps(msg) + '\n')
        
        controller = MessagesController(db_path=temp_db)
        
        # Import via CLI method
        options = ImportOptions(drop_existing=True)
        cli_result = controller.import_messages(file1, options)
        assert cli_result.total_imported == 2
        
        # Query via API
        app = FastAPI()
        app.include_router(controller.router)
        client = TestClient(app)
        
        # Upload different messages via API (without drop)
        with open(file2, 'rb') as f:
            api_response = client.post(
                "/messages/import",
                files={"file": ("messages.jsonl", f, "application/jsonl")},
                data={"drop_existing": "false"}
            )
        
        assert api_response.status_code == 200
        
        # Verify both imports worked
        session = controller.store.create_session()
        count = session.query(Message).count()
        assert count == 4  # 2 from CLI + 2 from API
        session.close()

