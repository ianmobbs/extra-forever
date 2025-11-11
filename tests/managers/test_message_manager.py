"""
Tests for app/managers/message_manager.py
"""
import pytest
from app.managers.message_manager import MessageManager
from models import Message


class TestMessageManager:
    """Test MessageManager class."""
    
    def test_bulk_create(self, db_session, sample_message):
        """Test bulk_create adds messages to database."""
        manager = MessageManager(db_session)
        
        messages = [sample_message]
        manager.bulk_create(messages)
        
        # Verify message was added
        count = db_session.query(Message).count()
        assert count == 1
        
        retrieved = db_session.query(Message).first()
        assert retrieved.id == "test123"
    
    def test_bulk_create_multiple(self, db_session):
        """Test bulk_create with multiple messages."""
        manager = MessageManager(db_session)
        
        messages = [
            Message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="test@example.com",
                to=["recipient@example.com"],
                body=f"Body {i}"
            )
            for i in range(5)
        ]
        
        manager.bulk_create(messages)
        
        count = db_session.query(Message).count()
        assert count == 5
    
    def test_get_first_n(self, db_session):
        """Test get_first_n retrieves correct number of messages."""
        manager = MessageManager(db_session)
        
        # Add 10 messages
        messages = [
            Message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="test@example.com",
                to=["recipient@example.com"],
                body=f"Body {i}"
            )
            for i in range(10)
        ]
        manager.bulk_create(messages)
        
        # Get first 5
        first_five = manager.get_first_n(5)
        assert len(first_five) == 5
        assert all(isinstance(msg, Message) for msg in first_five)
    
    def test_get_first_n_more_than_available(self, db_session):
        """Test get_first_n when requesting more than available."""
        manager = MessageManager(db_session)
        
        messages = [
            Message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="test@example.com",
                to=["recipient@example.com"],
                body=f"Body {i}"
            )
            for i in range(3)
        ]
        manager.bulk_create(messages)
        
        # Request 10 but only 3 exist
        result = manager.get_first_n(10)
        assert len(result) == 3
    
    def test_count(self, db_session):
        """Test count returns correct number."""
        manager = MessageManager(db_session)
        
        assert manager.count() == 0
        
        messages = [
            Message(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="test@example.com",
                to=["recipient@example.com"],
                body=f"Body {i}"
            )
            for i in range(7)
        ]
        manager.bulk_create(messages)
        
        assert manager.count() == 7

