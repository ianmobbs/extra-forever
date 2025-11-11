"""
Message manager for CRUD operations on Message entities.
"""
from typing import List
from sqlalchemy.orm import Session
from models import Message


class MessageManager:
    """Manages CRUD operations for Message entities."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def bulk_create(self, messages: List[Message]) -> None:
        """Bulk insert messages into the database."""
        self.session.add_all(messages)
        self.session.commit()
    
    def get_first_n(self, n: int) -> List[Message]:
        """Retrieve first n messages from the database."""
        return self.session.query(Message).limit(n).all()
    
    def count(self) -> int:
        """Count total messages in the database."""
        return self.session.query(Message).count()

