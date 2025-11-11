"""
Tests for models.py
"""
from datetime import datetime
import pytest
from models import Message, Base


class TestMessage:
    """Test Message ORM model."""
    
    def test_message_creation(self):
        """Test creating a Message instance."""
        msg = Message(
            id="test123",
            subject="Test Subject",
            sender="Test <test@example.com>",
            to=["recipient@example.com"],
            snippet="Test snippet",
            body="Test body",
            date=datetime(2025, 1, 1)
        )
        
        assert msg.id == "test123"
        assert msg.subject == "Test Subject"
        assert msg.sender == "Test <test@example.com>"
        assert msg.to == ["recipient@example.com"]
    
    def test_message_repr(self, sample_message):
        """Test Message string representation."""
        repr_str = repr(sample_message)
        assert "test123" in repr_str
        assert "Test Subject" in repr_str
        assert "test@example.com" in repr_str
    
    def test_message_repr_no_body(self):
        """Test Message repr with no body."""
        msg = Message(
            id="test",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            body=None,
            date=datetime.now()
        )
        repr_str = repr(msg)
        assert "test" in repr_str
    
    def test_message_database_fields(self, db_session, sample_message):
        """Test Message can be persisted to database."""
        db_session.add(sample_message)
        db_session.commit()
        
        retrieved = db_session.query(Message).filter_by(id="test123").first()
        assert retrieved is not None
        assert retrieved.subject == "Test Subject"
        assert retrieved.sender == "Test Sender <test@example.com>"

