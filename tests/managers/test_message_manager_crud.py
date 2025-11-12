"""
Tests for MessageManager CRUD operations.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.managers.message_manager import MessageManager
from models import Message


class TestMessageManagerCRUD:
    """Test MessageManager CRUD methods."""

    def test_create(self, db_session):
        """Test create adds message to database."""
        manager = MessageManager(db_session)

        message = manager.create(
            id="test123",
            subject="Test Subject",
            sender="sender@example.com",
            to=["recipient@example.com"],
            snippet="Test snippet",
            body="Test body",
            date=datetime(2025, 1, 1, 12, 0, 0),
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        assert message.id == "test123"
        assert message.subject == "Test Subject"
        assert message.sender == "sender@example.com"

        # Verify in database
        count = db_session.query(Message).count()
        assert count == 1

    def test_create_duplicate_id_raises_error(self, db_session):
        """Test creating message with duplicate ID raises IntegrityError on flush."""
        manager = MessageManager(db_session)

        manager.create(
            id="unique123",
            subject="First",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        with pytest.raises(IntegrityError):  # IntegrityError from flush
            manager.create(
                id="unique123",
                subject="Second",
                sender="sender@example.com",
                to=["recipient@example.com"],
            )

    def test_get_by_id(self, db_session):
        """Test get_by_id retrieves correct message."""
        manager = MessageManager(db_session)

        manager.create(
            id="find123",
            subject="Find Me",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        retrieved = manager.get_by_id("find123")
        assert retrieved is not None
        assert retrieved.id == "find123"
        assert retrieved.subject == "Find Me"

    def test_get_by_id_not_found(self, db_session):
        """Test get_by_id returns None for non-existent ID."""
        manager = MessageManager(db_session)

        result = manager.get_by_id("nonexistent")
        assert result is None

    def test_get_all(self, db_session):
        """Test get_all retrieves all messages."""
        manager = MessageManager(db_session)

        for i in range(5):
            manager.create(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"],
                date=datetime(2025, 1, i + 1, 12, 0, 0),
            )
        db_session.commit()  # Commit is now done by caller (service layer)

        all_messages = manager.get_all()
        assert len(all_messages) == 5
        assert all(isinstance(msg, Message) for msg in all_messages)
        # Check they are ordered by date descending
        assert all_messages[0].date > all_messages[-1].date

    def test_get_all_with_limit(self, db_session):
        """Test get_all with limit parameter."""
        manager = MessageManager(db_session)

        for i in range(10):
            manager.create(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"],
            )
        db_session.commit()  # Commit is now done by caller (service layer)

        messages = manager.get_all(limit=3)
        assert len(messages) == 3

    def test_get_all_with_offset(self, db_session):
        """Test get_all with offset parameter."""
        manager = MessageManager(db_session)

        for i in range(10):
            manager.create(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"],
                date=datetime(2025, 1, 1, 12, i, 0),
            )
        db_session.commit()  # Commit is now done by caller (service layer)

        messages = manager.get_all(offset=5)
        assert len(messages) == 5

    def test_get_all_with_limit_and_offset(self, db_session):
        """Test get_all with both limit and offset."""
        manager = MessageManager(db_session)

        for i in range(10):
            manager.create(
                id=f"msg{i}",
                subject=f"Subject {i}",
                sender="sender@example.com",
                to=["recipient@example.com"],
            )
        db_session.commit()  # Commit is now done by caller (service layer)

        messages = manager.get_all(limit=3, offset=2)
        assert len(messages) == 3

    def test_update_subject(self, db_session):
        """Test updating message subject."""
        manager = MessageManager(db_session)

        manager.create(
            id="update123",
            subject="Old Subject",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        updated = manager.update("update123", subject="New Subject")
        db_session.commit()  # Commit is now done by caller (service layer)
        assert updated is not None
        assert updated.subject == "New Subject"
        assert updated.sender == "sender@example.com"

    def test_update_multiple_fields(self, db_session):
        """Test updating multiple fields."""
        manager = MessageManager(db_session)

        manager.create(
            id="update123",
            subject="Old Subject",
            sender="old@example.com",
            to=["old@example.com"],
            snippet="Old snippet",
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        updated = manager.update(
            "update123", subject="New Subject", sender="new@example.com", snippet="New snippet"
        )
        db_session.commit()  # Commit is now done by caller (service layer)
        assert updated is not None
        assert updated.subject == "New Subject"
        assert updated.sender == "new@example.com"
        assert updated.snippet == "New snippet"

    def test_update_not_found(self, db_session):
        """Test updating non-existent message returns None."""
        manager = MessageManager(db_session)

        result = manager.update("nonexistent", subject="New Subject")
        assert result is None

    def test_update_body(self, db_session):
        """Test updating message body."""
        manager = MessageManager(db_session)

        manager.create(
            id="body_test",
            subject="Test",
            sender="sender@example.com",
            to=["recipient@example.com"],
            body="Old body",
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        updated = manager.update("body_test", body="New body")
        db_session.commit()  # Commit is now done by caller (service layer)
        assert updated is not None
        assert updated.body == "New body"

    def test_update_date(self, db_session):
        """Test updating message date."""
        manager = MessageManager(db_session)

        old_date = datetime(2025, 1, 1, 12, 0, 0)
        new_date = datetime(2025, 2, 1, 15, 30, 0)

        manager.create(
            id="date_test",
            subject="Test",
            sender="sender@example.com",
            to=["recipient@example.com"],
            date=old_date,
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        updated = manager.update("date_test", date=new_date)
        db_session.commit()  # Commit is now done by caller (service layer)
        assert updated is not None
        assert updated.date == new_date

    def test_update_all_optional_fields(self, db_session):
        """Test updating snippet, body, and date together."""
        manager = MessageManager(db_session)

        old_date = datetime(2025, 1, 1, 12, 0, 0)
        new_date = datetime(2025, 3, 1, 10, 0, 0)

        manager.create(
            id="all_fields_test",
            subject="Test",
            sender="sender@example.com",
            to=["recipient@example.com"],
            snippet="Old snippet",
            body="Old body",
            date=old_date,
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        updated = manager.update(
            "all_fields_test", snippet="New snippet", body="New body", date=new_date
        )
        db_session.commit()  # Commit is now done by caller (service layer)
        assert updated is not None
        assert updated.snippet == "New snippet"
        assert updated.body == "New body"
        assert updated.date == new_date

    def test_delete(self, db_session):
        """Test deleting a message."""
        manager = MessageManager(db_session)

        manager.create(
            id="delete123",
            subject="To Delete",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )
        db_session.commit()  # Commit is now done by caller (service layer)

        success = manager.delete("delete123")
        db_session.commit()  # Commit is now done by caller (service layer)
        assert success is True

        # Verify deleted
        retrieved = manager.get_by_id("delete123")
        assert retrieved is None

    def test_delete_not_found(self, db_session):
        """Test deleting non-existent message returns False."""
        manager = MessageManager(db_session)

        success = manager.delete("nonexistent")
        assert success is False
