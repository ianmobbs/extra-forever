"""
Messages service for orchestrating message import and processing.
"""
import json
import base64
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

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

