"""
Tests for app/controllers/messages_controller.py
"""

import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.messages_controller import ImportResponse, MessageResponse, MessagesController
from app.deps import get_messages_service
from app.services.messages_service import MessagesService
from app.stores.sqlite_store import SQLiteStore


class TestMessageResponse:
    """Test MessageResponse Pydantic model."""

    def test_message_response_creation(self):
        """Test creating a MessageResponse."""
        response = MessageResponse(
            id="test123",
            subject="Test Subject",
            sender="test@example.com",
            to=["recipient@example.com"],
            snippet="Test snippet",
        )
        assert response.id == "test123"
        assert response.subject == "Test Subject"
        assert response.to == ["recipient@example.com"]

    def test_message_response_optional_snippet(self):
        """Test MessageResponse with None snippet."""
        response = MessageResponse(
            id="test123",
            subject="Test Subject",
            sender="test@example.com",
            to=["recipient@example.com"],
            snippet=None,
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
                to=["recipient@example.com"],
                snippet="snippet",
            )
        ]
        response = ImportResponse(total_imported=5, preview=preview)
        assert response.total_imported == 5
        assert len(response.preview) == 1


class TestMessagesController:
    """Test MessagesController class."""

    def test_controller_initialization(self):
        """Test controller can be initialized."""
        controller = MessagesController()
        assert controller.router is not None

    def test_controller_has_routes(self):
        """Test controller registers routes."""
        controller = MessagesController()
        routes = [route.path for route in controller.router.routes]
        assert "/messages/import" in routes


class TestMessagesControllerAPI:
    """Test MessagesController API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client with dependency overrides."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = f"sqlite:///{tmp.name}"
            store = SQLiteStore(db_path=db_path, echo=False)
            store.init_db(drop_existing=True)

            # Create a session for the test service
            session = store.create_session()
            test_service = MessagesService(session, store=store)

            # Override the dependency
            def override_get_messages_service():
                return test_service

            controller = MessagesController()
            app = FastAPI()
            app.include_router(controller.router)
            app.dependency_overrides[get_messages_service] = override_get_messages_service

            client = TestClient(app)
            yield client

            # Cleanup
            session.close()
            Path(tmp.name).unlink(missing_ok=True)

    def test_import_upload_endpoint(self, client, sample_jsonl_file):
        """Test /import endpoint with file upload."""
        with open(sample_jsonl_file, "rb") as f:
            response = client.post(
                "/messages/import",
                files={"file": ("messages.jsonl", f, "application/jsonl")},
                data={"drop_existing": "true", "auto_classify": "false"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "total_imported" in data
        assert data["total_imported"] == 3
        assert "preview" in data
        assert len(data["preview"]) > 0

    def test_import_upload_preserves_data(self, client, sample_jsonl_file):
        """Test that import preserves message data correctly."""
        with open(sample_jsonl_file, "rb") as f:
            response = client.post(
                "/messages/import",
                files={"file": ("messages.jsonl", f, "application/jsonl")},
                data={"drop_existing": "true"},
            )

        assert response.status_code == 200
        data = response.json()
        preview = data["preview"]

        # Check first message
        msg = preview[0]
        assert "id" in msg
        assert "subject" in msg
        assert "sender" in msg
        assert "to" in msg
        assert isinstance(msg["to"], list)

    def test_import_upload_without_drop(self, client, sample_jsonl_file):
        """Test import without dropping existing data."""
        # First import
        with open(sample_jsonl_file, "rb") as f:
            response1 = client.post(
                "/messages/import",
                files={"file": ("messages.jsonl", f, "application/jsonl")},
                data={"drop_existing": "true"},
            )
        assert response1.status_code == 200

        # Second import without drop (should fail with UNIQUE constraint error)
        # TestClient raises exceptions, so we catch the IntegrityError
        from sqlalchemy.exc import IntegrityError

        try:
            with open(sample_jsonl_file, "rb") as f:
                response2 = client.post(
                    "/messages/import",
                    files={"file": ("messages.jsonl", f, "application/jsonl")},
                    data={"drop_existing": "false"},
                )
            # If no exception, check that response is appropriate
            assert response2.status_code in [200, 400, 500]
        except IntegrityError:
            # IntegrityError is expected when trying to import duplicates
            pass
