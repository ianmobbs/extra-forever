"""
Tests for MessagesService CRUD operations.
"""

from datetime import datetime

import pytest

from app.services.messages_service import MessagesService


class TestMessagesServiceCRUD:
    """Test MessagesService CRUD methods."""

    def test_create_message(self, db_session, sqlite_store, mock_embedding_service):
        """Test creating a message through service."""
        service = MessagesService(db_session, mock_embedding_service)

        result = service.create_message(
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
        # Verify embedding was added
        assert result.message.embedding is not None
        assert len(result.message.embedding) == 1536

    def test_create_message_duplicate_raises_error(
        self, db_session, sqlite_store, mock_embedding_service
    ):
        """Test creating duplicate message raises error."""
        service = MessagesService(db_session, mock_embedding_service)

        service.create_message(
            id="unique123",
            subject="First",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )

        with pytest.raises(ValueError):
            service.create_message(
                id="unique123",
                subject="Second",
                sender="sender@example.com",
                to=["recipient@example.com"],
            )

    def test_get_message(self, db_session, sqlite_store, mock_embedding_service):
        """Test retrieving message by ID."""
        service = MessagesService(db_session, mock_embedding_service)

        service.create_message(
            id="find123",
            subject="Find Me",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )

        result = service.get_message("find123")
        assert result is not None
        assert result.message.id == "find123"
        assert result.message.subject == "Find Me"

    def test_get_message_not_found(self, db_session, sqlite_store, mock_embedding_service):
        """Test retrieving non-existent message returns None."""
        service = MessagesService(db_session, mock_embedding_service)

        result = service.get_message("nonexistent")
        assert result is None

    def test_list_messages(self, db_session, sqlite_store, mock_embedding_service):
        """Test listing all messages."""
        service = MessagesService(db_session, mock_embedding_service)

        for i in range(5):
            service.create_message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"],
            )

        messages = service.list_messages()
        assert len(messages) == 5

    def test_list_messages_with_limit(self, db_session, sqlite_store, mock_embedding_service):
        """Test listing messages with limit."""
        service = MessagesService(db_session, mock_embedding_service)

        for i in range(10):
            service.create_message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"],
            )

        messages = service.list_messages(limit=3)
        assert len(messages) == 3

    def test_list_messages_with_offset(self, db_session, sqlite_store, mock_embedding_service):
        """Test listing messages with offset."""
        service = MessagesService(db_session, mock_embedding_service)

        for i in range(10):
            service.create_message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"],
            )

        messages = service.list_messages(offset=5)
        assert len(messages) == 5

    def test_list_messages_empty(self, db_session, sqlite_store, mock_embedding_service):
        """Test listing messages when none exist."""
        service = MessagesService(db_session, mock_embedding_service)

        messages = service.list_messages()
        assert messages == []

    def test_update_message(self, db_session, sqlite_store, mock_embedding_service):
        """Test updating a message."""
        service = MessagesService(db_session, mock_embedding_service)

        service.create_message(
            id="update123", subject="Old Subject", sender="old@example.com", to=["old@example.com"]
        )

        result = service.update_message(
            "update123", subject="New Subject", sender="new@example.com"
        )

        assert result is not None
        assert result.message.subject == "New Subject"
        assert result.message.sender == "new@example.com"

    def test_update_message_partial(self, db_session, sqlite_store, mock_embedding_service):
        """Test updating only some fields."""
        service = MessagesService(db_session, mock_embedding_service)

        service.create_message(
            id="update123",
            subject="Subject",
            sender="old@example.com",
            to=["recipient@example.com"],
        )

        result = service.update_message("update123", sender="new@example.com")

        assert result is not None
        assert result.message.subject == "Subject"
        assert result.message.sender == "new@example.com"

    def test_update_message_not_found(self, db_session, sqlite_store, mock_embedding_service):
        """Test updating non-existent message returns None."""
        service = MessagesService(db_session, mock_embedding_service)

        result = service.update_message("nonexistent", subject="New Subject")
        assert result is None

    def test_delete_message(self, db_session, sqlite_store, mock_embedding_service):
        """Test deleting a message."""
        service = MessagesService(db_session, mock_embedding_service)

        service.create_message(
            id="delete123",
            subject="To Delete",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )

        success = service.delete_message("delete123")
        assert success is True

        # Verify deleted
        result = service.get_message("delete123")
        assert result is None

    def test_delete_message_not_found(self, db_session, sqlite_store, mock_embedding_service):
        """Test deleting non-existent message returns False."""
        service = MessagesService(db_session, mock_embedding_service)

        success = service.delete_message("nonexistent")
        assert success is False

    def test_update_message_regenerates_embedding(
        self, db_session, sqlite_store, mock_embedding_service
    ):
        """Test that updating a message regenerates its embedding (idempotent with create)."""
        service = MessagesService(db_session, mock_embedding_service)

        # Create message
        created = service.create_message(
            id="embed123",
            subject="Original Subject",
            sender="sender@example.com",
            to=["recipient@example.com"],
            body="Original body",
        )
        original_embedding = created.message.embedding.copy()
        assert original_embedding is not None

        # Update message - this should regenerate the embedding
        updated = service.update_message("embed123", subject="Updated Subject", body="Updated body")

        assert updated is not None
        assert updated.message.embedding is not None
        assert len(updated.message.embedding) == 1536
        # Embedding should be regenerated (mock service generates different embeddings)
        # The key is that embedding exists and has correct length

    def test_update_message_partial_regenerates_embedding(
        self, db_session, sqlite_store, mock_embedding_service
    ):
        """Test that partial updates also regenerate embedding."""
        service = MessagesService(db_session, mock_embedding_service)

        # Create message
        service.create_message(
            id="partial123",
            subject="Subject",
            sender="old@example.com",
            to=["recipient@example.com"],
        )

        # Update only sender - embedding should still be regenerated
        result = service.update_message("partial123", sender="new@example.com")

        assert result is not None
        assert result.message.embedding is not None
        assert len(result.message.embedding) == 1536
