"""
Message manager for CRUD operations on Message entities.
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from models import Message


class MessageManager:
    """Manages CRUD operations for Message entities."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        id: str,
        subject: str,
        sender: str,
        to: List[str],
        snippet: Optional[str] = None,
        body: Optional[str] = None,
        date: Optional[datetime] = None,
        embedding: Optional[List[float]] = None
    ) -> Message:
        """Create a new message."""
        message = Message(
            id=id,
            subject=subject,
            sender=sender,
            to=to,
            snippet=snippet,
            body=body,
            date=date,
            embedding=embedding
        )
        self.session.add(message)
        try:
            self.session.commit()
            # Re-query with eager loading to ensure categories are loaded
            return self.session.query(Message).options(joinedload(Message.categories)).filter(Message.id == id).first()
        except IntegrityError:
            self.session.rollback()
            raise ValueError(f"Message with id '{id}' already exists")
    
    def bulk_create(self, messages: List[Message]) -> None:
        """Bulk insert messages into the database."""
        self.session.add_all(messages)
        self.session.commit()
    
    def get_by_id(self, message_id: str) -> Optional[Message]:
        """Get a message by ID."""
        return self.session.query(Message).options(joinedload(Message.categories)).filter(Message.id == message_id).first()
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Message]:
        """Get all messages with optional pagination."""
        query = self.session.query(Message).options(joinedload(Message.categories)).order_by(Message.date.desc().nullslast())
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()
    
    def get_first_n(self, n: int) -> List[Message]:
        """Retrieve first n messages from the database."""
        return self.session.query(Message).options(joinedload(Message.categories)).limit(n).all()
    
    def update(
        self,
        message_id: str,
        subject: Optional[str] = None,
        sender: Optional[str] = None,
        to: Optional[List[str]] = None,
        snippet: Optional[str] = None,
        body: Optional[str] = None,
        date: Optional[datetime] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[Message]:
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
        
        self.session.commit()
        # Re-query with eager loading
        return self.session.query(Message).options(joinedload(Message.categories)).filter(Message.id == message_id).first()
    
    def delete(self, message_id: str) -> bool:
        """Delete a message by ID."""
        message = self.get_by_id(message_id)
        if not message:
            return False
        
        self.session.delete(message)
        self.session.commit()
        return True
    
    def count(self) -> int:
        """Count total messages in the database."""
        return self.session.query(Message).count()

