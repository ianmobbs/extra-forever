"""
Message manager for CRUD operations on Message entities.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from models import Message

logger = logging.getLogger(__name__)


class MessageManager:
    """Manages CRUD operations for Message entities."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        id: str,
        subject: str,
        sender: str,
        to: list[str],
        snippet: str | None = None,
        body: str | None = None,
        date: datetime | None = None,
        embedding: list[float] | None = None,
    ) -> Message:
        """Create a new message."""
        logger.debug(f"MessageManager: Creating message '{id[:30]}...'")
        message = Message(
            id=id,
            subject=subject,
            sender=sender,
            to=to,
            snippet=snippet,
            body=body,
            date=date,
            embedding=embedding,
        )
        self.session.add(message)
        self.session.flush()  # Flush to catch IntegrityError before commit
        logger.debug(f"MessageManager: Message '{id[:30]}...' created")
        # Re-query with eager loading to ensure message_categories are loaded
        from models import MessageCategory

        return (
            self.session.query(Message)
            .options(joinedload(Message.message_categories).joinedload(MessageCategory.category))
            .filter(Message.id == id)
            .first()
        )

    def bulk_create(self, messages: list[Message]) -> None:
        """Bulk insert messages into the database."""
        logger.debug(f"MessageManager: Bulk creating {len(messages)} messages")
        self.session.add_all(messages)
        self.session.flush()  # Flush to ensure messages are staged
        logger.debug(f"MessageManager: Bulk creation of {len(messages)} messages completed")

    def get_by_id(self, message_id: str) -> Message | None:
        """Get a message by ID."""
        logger.debug(f"MessageManager: Retrieving message '{message_id[:30]}...'")
        from models import MessageCategory

        return (
            self.session.query(Message)
            .options(joinedload(Message.message_categories).joinedload(MessageCategory.category))
            .filter(Message.id == message_id)
            .first()
        )

    def get_all(self, limit: int | None = None, offset: int | None = None) -> list[Message]:
        """Get all messages with optional pagination."""
        from models import MessageCategory

        query = (
            self.session.query(Message)
            .options(joinedload(Message.message_categories).joinedload(MessageCategory.category))
            .order_by(Message.date.desc().nullslast())
        )
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get_first_n(self, n: int) -> list[Message]:
        """Retrieve first n messages from the database."""
        from models import MessageCategory

        return (
            self.session.query(Message)
            .options(joinedload(Message.message_categories).joinedload(MessageCategory.category))
            .limit(n)
            .all()
        )

    def update(
        self,
        message_id: str,
        subject: str | None = None,
        sender: str | None = None,
        to: list[str] | None = None,
        snippet: str | None = None,
        body: str | None = None,
        date: datetime | None = None,
        embedding: list[float] | None = None,
    ) -> Message | None:
        """Update a message by ID."""
        message = self.get_by_id(message_id)
        if not message:
            return None

        if subject is not None:
            message.subject = subject
        if sender is not None:
            message.sender = sender
        if to is not None:
            message.to = to
        if snippet is not None:
            message.snippet = snippet
        if body is not None:
            message.body = body
        if date is not None:
            message.date = date
        if embedding is not None:
            message.embedding = embedding

        self.session.flush()  # Flush to ensure updates are staged
        # Re-query with eager loading
        from models import MessageCategory

        return (
            self.session.query(Message)
            .options(joinedload(Message.message_categories).joinedload(MessageCategory.category))
            .filter(Message.id == message_id)
            .first()
        )

    def delete(self, message_id: str) -> bool:
        """Delete a message by ID."""
        message = self.get_by_id(message_id)
        if not message:
            return False

        self.session.delete(message)
        self.session.flush()  # Flush to ensure delete is staged
        return True

    def count(self) -> int:
        """Count total messages in the database."""
        return self.session.query(Message).count()
