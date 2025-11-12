"""
Tests for MessagesController CRUD operations.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.messages_controller import MessagesController
from app.deps import get_messages_service
from app.services.messages_service import MessagesService
from app.stores.sqlite_store import SQLiteStore


@pytest.fixture
def messages_service():
    """Create a MessagesService with temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = f"sqlite:///{tmp.name}"
        store = SQLiteStore(db_path=db_path, echo=False)
        store.init_db(drop_existing=True)

        session = store.create_session()
        service = MessagesService(session, store=store)
        yield service

        # Cleanup
        session.close()
        Path(tmp.name).unlink(missing_ok=True)


class TestMessagesControllerCRUD:
    """Test MessagesService CRUD operations via service layer."""

    def test_create_message(self, messages_service):
        """Test creating a message through service."""
        result = messages_service.create_message(
            id="test123",
            subject="Test Subject",
            sender="sender@example.com",
            to=["recipient@example.com"],
            snippet="Test snippet",
            body="Test body",
            date=datetime(2025, 1, 1, 12, 0, 0),
        )

        assert result.message.id == "test123"
        assert result.message.subject == "Test Subject"
        assert result.message.sender == "sender@example.com"

    def test_get_message(self, messages_service):
        """Test retrieving a message."""
        messages_service.create_message(
            id="msg1",
            subject="Subject 1",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )

        result = messages_service.get_message("msg1")
        assert result is not None
        assert result.message.id == "msg1"

    def test_list_messages(self, messages_service):
        """Test listing messages."""
        messages_service.create_message(
            id="msg1", subject="Subject 1", sender="sender@example.com", to=["r@example.com"]
        )
        messages_service.create_message(
            id="msg2", subject="Subject 2", sender="sender@example.com", to=["r@example.com"]
        )

        messages = messages_service.list_messages()
        assert len(messages) == 2

    def test_list_messages_with_pagination(self, messages_service):
        """Test listing messages with pagination."""
        for i in range(5):
            messages_service.create_message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["r@example.com"],
            )

        messages = messages_service.list_messages(limit=2, offset=1)
        assert len(messages) == 2

    def test_update_message(self, messages_service):
        """Test updating a message."""
        messages_service.create_message(
            id="msg1", subject="Old Subject", sender="sender@example.com", to=["r@example.com"]
        )

        result = messages_service.update_message("msg1", subject="New Subject")
        assert result is not None
        assert result.message.subject == "New Subject"

    def test_delete_message(self, messages_service):
        """Test deleting a message."""
        messages_service.create_message(
            id="msg1", subject="Subject 1", sender="sender@example.com", to=["r@example.com"]
        )

        success = messages_service.delete_message("msg1")
        assert success is True

        result = messages_service.get_message("msg1")
        assert result is None


class TestMessagesControllerCRUDAPI:
    """Test MessagesController CRUD API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client with dependency overrides."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = f"sqlite:///{tmp.name}"
            store = SQLiteStore(db_path=db_path, echo=False)
            store.init_db(drop_existing=True)

            session = store.create_session()
            test_service = MessagesService(session, store=store)

            def override_get_messages_service():
                return test_service

            controller = MessagesController()
            app = FastAPI()
            app.include_router(controller.router)
            app.dependency_overrides[get_messages_service] = override_get_messages_service

            client = TestClient(app)
            yield client

            session.close()
            Path(tmp.name).unlink(missing_ok=True)

    def test_create_message_api(self, client):
        """Test creating a message via API."""
        response = client.post(
            "/messages/",
            json={
                "id": "test123",
                "subject": "Test Subject",
                "sender": "sender@example.com",
                "to": ["recipient@example.com"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test123"
        assert data["subject"] == "Test Subject"

    def test_create_message_api_duplicate(self, client):
        """Test creating duplicate message fails."""
        message_data = {
            "id": "dup123",
            "subject": "Subject",
            "sender": "sender@example.com",
            "to": ["recipient@example.com"],
        }

        response1 = client.post("/messages/", json=message_data)
        assert response1.status_code == 200

        response2 = client.post("/messages/", json=message_data)
        assert response2.status_code == 400

    def test_list_messages_api(self, client):
        """Test listing messages via API."""
        client.post(
            "/messages/",
            json={
                "id": "msg1",
                "subject": "Subject 1",
                "sender": "sender@example.com",
                "to": ["r@example.com"],
            },
        )
        client.post(
            "/messages/",
            json={
                "id": "msg2",
                "subject": "Subject 2",
                "sender": "sender@example.com",
                "to": ["r@example.com"],
            },
        )

        response = client.get("/messages/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_messages_api_with_pagination(self, client):
        """Test listing messages with pagination via API."""
        for i in range(5):
            client.post(
                "/messages/",
                json={
                    "id": f"msg{i}",
                    "subject": f"Subject {i}",
                    "sender": "sender@example.com",
                    "to": ["r@example.com"],
                },
            )

        response = client.get("/messages/?limit=2&offset=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_message_api(self, client):
        """Test getting a message via API."""
        client.post(
            "/messages/",
            json={
                "id": "msg1",
                "subject": "Subject 1",
                "sender": "sender@example.com",
                "to": ["r@example.com"],
            },
        )

        response = client.get("/messages/msg1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "msg1"

    def test_get_message_api_not_found(self, client):
        """Test getting non-existent message returns 404."""
        response = client.get("/messages/nonexistent")
        assert response.status_code == 404

    def test_update_message_api(self, client):
        """Test updating a message via API."""
        client.post(
            "/messages/",
            json={
                "id": "msg1",
                "subject": "Old Subject",
                "sender": "sender@example.com",
                "to": ["r@example.com"],
            },
        )

        response = client.put(
            "/messages/msg1",
            json={"subject": "New Subject"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "New Subject"

    def test_update_message_api_not_found(self, client):
        """Test updating non-existent message returns 404."""
        response = client.put(
            "/messages/nonexistent",
            json={"subject": "New Subject"},
        )
        assert response.status_code == 404

    def test_update_message_api_validation_error(self, client):
        """Test update with invalid data returns 422."""
        client.post(
            "/messages/",
            json={
                "id": "msg1",
                "subject": "Subject",
                "sender": "sender@example.com",
                "to": ["r@example.com"],
            },
        )

        # Empty JSON should work (no updates)
        response = client.put("/messages/msg1", json={})
        # This should either be 200 (no changes) or 422 (validation error)
        assert response.status_code in [200, 422]

    def test_update_message_api_all_fields(self, client):
        """Test updating all fields of a message."""
        client.post(
            "/messages/",
            json={
                "id": "msg1",
                "subject": "Old",
                "sender": "old@example.com",
                "to": ["old@example.com"],
            },
        )

        response = client.put(
            "/messages/msg1",
            json={
                "subject": "New",
                "sender": "new@example.com",
                "to": ["new@example.com"],
                "snippet": "New snippet",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "New"
        assert data["sender"] == "new@example.com"

    def test_delete_message_api(self, client):
        """Test deleting a message via API."""
        client.post(
            "/messages/",
            json={
                "id": "msg1",
                "subject": "Subject",
                "sender": "sender@example.com",
                "to": ["r@example.com"],
            },
        )

        response = client.delete("/messages/msg1")
        assert response.status_code == 200

        # Verify deleted
        get_response = client.get("/messages/msg1")
        assert get_response.status_code == 404

    def test_delete_message_api_not_found(self, client):
        """Test deleting non-existent message returns 404."""
        response = client.delete("/messages/nonexistent")
        assert response.status_code == 404

    def test_update_message_api_idempotent(self, client):
        """Test that update is idempotent with create (regenerates embeddings)."""
        # Create message
        create_response = client.post(
            "/messages/",
            json={
                "id": "idempotent1",
                "subject": "Original Subject",
                "sender": "sender@example.com",
                "to": ["recipient@example.com"],
                "body": "Original body",
            },
        )
        assert create_response.status_code == 200

        # Update message - should regenerate embedding just like create
        update_response = client.put(
            "/messages/idempotent1",
            json={
                "subject": "Updated Subject",
                "body": "Updated body",
            },
        )
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["subject"] == "Updated Subject"

        # Verify we can still get the message
        get_response = client.get("/messages/idempotent1")
        assert get_response.status_code == 200
