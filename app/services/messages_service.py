"""
Messages service for orchestrating message import and processing.
"""
import json
import base64
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models import Message
from app.managers.message_manager import MessageManager
from app.stores.sqlite_store import SQLiteStore


@dataclass
class ImportResult:
    """Result of a message import operation."""
    total_imported: int
    preview_messages: List[Message]


@dataclass
class ImportOptions:
    """Options for message import."""
    drop_existing: bool = True


@dataclass
class MessageResult:
    """Result of a message operation."""
    message: Message


class MessagesService:
    """Service for orchestrating message import and processing operations."""
    
    def __init__(self, store: SQLiteStore):
        self.store = store
    
    def import_from_jsonl(
        self,
        file_path: Path,
        options: ImportOptions
    ) -> ImportResult:
        """
        Import messages from a JSONL file.
        
        Args:
            file_path: Path to the JSONL file
            options: Import configuration options
            
        Returns:
            ImportResult with count and preview messages
        """
        # Initialize database
        self.store.init_db(drop_existing=options.drop_existing)
        
        # Parse messages from file
        messages = self._parse_jsonl_file(file_path)
        
        # Store messages
        session = self.store.create_session()
        try:
            manager = MessageManager(session)
            manager.bulk_create(messages)
            
            # Get preview
            preview = manager.get_first_n(5)
            
            return ImportResult(
                total_imported=len(messages),
                preview_messages=preview
            )
        finally:
            session.close()
    
    def _parse_jsonl_file(self, file_path: Path) -> List[Message]:
        """Parse JSONL file and convert to Message objects."""
        messages = []
        
        with open(file_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                
                # Decode body
                body_decoded = base64.b64decode(data['body']).decode('utf-8', errors='replace')
                
                # Parse date
                date_obj = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                
                message = Message(
                    id=data['id'],
                    subject=data['subject'],
                    sender=data['from'],
                    to=data['to'],
                    snippet=data.get('snippet'),
                    body=body_decoded,
                    date=date_obj
                )
                messages.append(message)
        
        return messages
    
    def create_message(
        self,
        id: str,
        subject: str,
        sender: str,
        to: List[str],
        snippet: Optional[str] = None,
        body: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> MessageResult:
        """
        Create a new message.
        
        Args:
            id: Unique message ID
            subject: Message subject
            sender: Sender email
            to: List of recipient emails
            snippet: Short preview text
            body: Full message body
            date: Message date
            
        Returns:
            MessageResult with the created message
        """
        session = self.store.create_session()
        try:
            manager = MessageManager(session)
            message = manager.create(
                id=id,
                subject=subject,
                sender=sender,
                to=to,
                snippet=snippet,
                body=body,
                date=date
            )
            return MessageResult(message=message)
        finally:
            session.close()
    
    def get_message(self, message_id: str) -> Optional[MessageResult]:
        """
        Get a message by ID.
        
        Args:
            message_id: Message ID
            
        Returns:
            MessageResult or None if not found
        """
        session = self.store.create_session()
        try:
            manager = MessageManager(session)
            message = manager.get_by_id(message_id)
            if message:
                return MessageResult(message=message)
            return None
        finally:
            session.close()
    
    def list_messages(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Message]:
        """
        List all messages with optional pagination.
        
        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of messages
        """
        session = self.store.create_session()
        try:
            manager = MessageManager(session)
            return manager.get_all(limit=limit, offset=offset)
        finally:
            session.close()
    
    def update_message(
        self,
        message_id: str,
        subject: Optional[str] = None,
        sender: Optional[str] = None,
        to: Optional[List[str]] = None,
        snippet: Optional[str] = None,
        body: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> Optional[MessageResult]:
        """
        Update a message.
        
        Args:
            message_id: Message ID
            subject: New subject (optional)
            sender: New sender (optional)
            to: New recipients (optional)
            snippet: New snippet (optional)
            body: New body (optional)
            date: New date (optional)
            
        Returns:
            MessageResult or None if not found
        """
        session = self.store.create_session()
        try:
            manager = MessageManager(session)
            message = manager.update(
                message_id,
                subject=subject,
                sender=sender,
                to=to,
                snippet=snippet,
                body=body,
                date=date
            )
            if message:
                return MessageResult(message=message)
            return None
        finally:
            session.close()
    
    def delete_message(self, message_id: str) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: Message ID
            
        Returns:
            True if deleted, False if not found
        """
        session = self.store.create_session()
        try:
            manager = MessageManager(session)
            return manager.delete(message_id)
        finally:
            session.close()

