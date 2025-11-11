"""
Tests for MessagesController CRUD operations.
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from app.controllers.messages_controller import MessagesController


@pytest.fixture
def controller():
    """Create a MessagesController with temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = f"sqlite:///{tmp.name}"
        controller = MessagesController(db_path=db_path)
        # Initialize the database
        controller.store.init_db(drop_existing=False)
        yield controller
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)


class TestMessagesControllerCRUD:
    """Test MessagesController CRUD methods."""
    
    def test_create_message(self, controller):
        """Test creating a message through controller."""
        result = controller.create_message(
            id="test123",
            subject="Test Subject",
            sender="sender@example.com",
            to=["recipient@example.com"],
            snippet="Test snippet",
            body="Test body",
            date=datetime(2025, 1, 1, 12, 0, 0)
        )
        
        assert result.message.id == "test123"
        assert result.message.subject == "Test Subject"
    
    def test_get_message(self, controller):
        """Test retrieving a message."""
        created = controller.create_message(
            id="find123",
            subject="Find Me",
            sender="sender@example.com",
            to=["recipient@example.com"]
        )
        
        result = controller.get_message("find123")
        assert result is not None
        assert result.message.id == "find123"
    
    def test_list_messages(self, controller):
        """Test listing all messages."""
        for i in range(5):
            controller.create_message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"]
            )
        
        messages = controller.list_messages()
        assert len(messages) == 5
    
    def test_list_messages_with_pagination(self, controller):
        """Test listing messages with pagination."""
        for i in range(10):
            controller.create_message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"]
            )
        
        messages = controller.list_messages(limit=3, offset=2)
        assert len(messages) == 3
    
    def test_update_message(self, controller):
        """Test updating a message."""
        created = controller.create_message(
            id="update123",
            subject="Old Subject",
            sender="old@example.com",
            to=["old@example.com"]
        )
        
        result = controller.update_message(
            "update123",
            subject="New Subject",
            sender="new@example.com"
        )
        
        assert result is not None
        assert result.message.subject == "New Subject"
        assert result.message.sender == "new@example.com"
    
    def test_delete_message(self, controller):
        """Test deleting a message."""
        created = controller.create_message(
            id="delete123",
            subject="To Delete",
            sender="sender@example.com",
            to=["recipient@example.com"]
        )
        
        success = controller.delete_message("delete123")
        assert success is True
        
        # Verify deleted
        result = controller.get_message("delete123")
        assert result is None

