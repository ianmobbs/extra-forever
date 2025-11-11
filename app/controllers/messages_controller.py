"""
Messages controller for handling CLI and API requests.
"""
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.services.messages_service import MessagesService, ImportOptions, ImportResult
from app.stores.sqlite_store import SQLiteStore


class MessageResponse(BaseModel):
    """API response model for a message."""
    id: str
    subject: str
    sender: str
    to: List[str]
    snippet: Optional[str] = None
    body: Optional[str] = None
    date: Optional[datetime] = None


class MessageCreateRequest(BaseModel):
    """API request model for creating a message."""
    id: str
    subject: str
    sender: str
    to: List[str]
    snippet: Optional[str] = None
    body: Optional[str] = None
    date: Optional[datetime] = None


class MessageUpdateRequest(BaseModel):
    """API request model for updating a message."""
    subject: Optional[str] = None
    sender: Optional[str] = None
    to: Optional[List[str]] = None
    snippet: Optional[str] = None
    body: Optional[str] = None
    date: Optional[datetime] = None


class ImportResponse(BaseModel):
    """API response for import operation."""
    total_imported: int
    preview: List[MessageResponse]


class MessagesController:
    """Controller for message-related operations."""
    
    def __init__(self, db_path: str = "sqlite:///messages.db"):
        self.store = SQLiteStore(db_path=db_path, echo=False)
        self.router = APIRouter(prefix="/messages", tags=["messages"])
        self._register_routes()
    
    def _register_routes(self):
        """Register FastAPI routes."""
        self.router.post("/import", response_model=ImportResponse)(self.import_upload)
        self.router.post("/", response_model=MessageResponse)(self.create_message_api)
        self.router.get("/", response_model=List[MessageResponse])(self.list_messages_api)
        self.router.get("/{message_id}", response_model=MessageResponse)(self.get_message_api)
        self.router.put("/{message_id}", response_model=MessageResponse)(self.update_message_api)
        self.router.delete("/{message_id}")(self.delete_message_api)
    
    async def import_upload(
        self,
        file: UploadFile = File(...),
        drop_existing: bool = Form(True)
    ) -> ImportResponse:
        """
        API endpoint: Handle file upload and import messages.
        
        Wraps the uploaded file in a tempfile, then delegates to import_messages.
        """
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.jsonl') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            options = ImportOptions(drop_existing=drop_existing)
            result = self.import_messages(Path(tmp_path), options)
            
            # Convert to API response
            preview = [
                MessageResponse(
                    id=msg.id,
                    subject=msg.subject,
                    sender=msg.sender,
                    to=msg.to,
                    snippet=msg.snippet,
                    body=msg.body,
                    date=msg.date
                )
                for msg in result.preview_messages
            ]
            
            return ImportResponse(
                total_imported=result.total_imported,
                preview=preview
            )
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
    
    def import_messages(
        self,
        file_path: Path,
        options: ImportOptions
    ) -> ImportResult:
        """
        Import messages from a JSONL file.
        
        Core import logic used by both CLI and API interfaces.
        
        Args:
            file_path: Path to the JSONL file
            options: Import configuration options
            
        Returns:
            ImportResult with import statistics
        """
        service = MessagesService(self.store)
        return service.import_from_jsonl(file_path, options)
    
    async def create_message_api(self, request: MessageCreateRequest) -> MessageResponse:
        """
        API endpoint: Create a new message.
        """
        try:
            result = self.create_message(
                id=request.id,
                subject=request.subject,
                sender=request.sender,
                to=request.to,
                snippet=request.snippet,
                body=request.body,
                date=request.date
            )
            return MessageResponse(
                id=result.message.id,
                subject=result.message.subject,
                sender=result.message.sender,
                to=result.message.to,
                snippet=result.message.snippet,
                body=result.message.body,
                date=result.message.date
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def list_messages_api(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[MessageResponse]:
        """
        API endpoint: List all messages.
        """
        messages = self.list_messages(limit=limit, offset=offset)
        return [
            MessageResponse(
                id=msg.id,
                subject=msg.subject,
                sender=msg.sender,
                to=msg.to,
                snippet=msg.snippet,
                body=msg.body,
                date=msg.date
            )
            for msg in messages
        ]
    
    async def get_message_api(self, message_id: str) -> MessageResponse:
        """
        API endpoint: Get a message by ID.
        """
        result = self.get_message(message_id)
        if not result:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return MessageResponse(
            id=result.message.id,
            subject=result.message.subject,
            sender=result.message.sender,
            to=result.message.to,
            snippet=result.message.snippet,
            body=result.message.body,
            date=result.message.date
        )
    
    async def update_message_api(
        self,
        message_id: str,
        request: MessageUpdateRequest
    ) -> MessageResponse:
        """
        API endpoint: Update a message.
        """
        try:
            result = self.update_message(
                message_id,
                subject=request.subject,
                sender=request.sender,
                to=request.to,
                snippet=request.snippet,
                body=request.body,
                date=request.date
            )
            if not result:
                raise HTTPException(status_code=404, detail="Message not found")
            
            return MessageResponse(
                id=result.message.id,
                subject=result.message.subject,
                sender=result.message.sender,
                to=result.message.to,
                snippet=result.message.snippet,
                body=result.message.body,
                date=result.message.date
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def delete_message_api(self, message_id: str):
        """
        API endpoint: Delete a message.
        """
        success = self.delete_message(message_id)
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {"message": "Message deleted successfully"}
    
    # CLI-friendly methods
    
    def create_message(
        self,
        id: str,
        subject: str,
        sender: str,
        to: List[str],
        snippet: Optional[str] = None,
        body: Optional[str] = None,
        date: Optional[datetime] = None
    ):
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
        service = MessagesService(self.store)
        return service.create_message(id, subject, sender, to, snippet, body, date)
    
    def get_message(self, message_id: str):
        """
        Get a message by ID.
        
        Args:
            message_id: Message ID
            
        Returns:
            MessageResult or None
        """
        service = MessagesService(self.store)
        return service.get_message(message_id)
    
    def list_messages(self, limit: Optional[int] = None, offset: Optional[int] = None):
        """
        List all messages.
        
        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of Message objects
        """
        service = MessagesService(self.store)
        return service.list_messages(limit=limit, offset=offset)
    
    def update_message(
        self,
        message_id: str,
        subject: Optional[str] = None,
        sender: Optional[str] = None,
        to: Optional[List[str]] = None,
        snippet: Optional[str] = None,
        body: Optional[str] = None,
        date: Optional[datetime] = None
    ):
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
            MessageResult or None
        """
        service = MessagesService(self.store)
        return service.update_message(message_id, subject, sender, to, snippet, body, date)
    
    def delete_message(self, message_id: str) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: Message ID
            
        Returns:
            True if deleted, False if not found
        """
        service = MessagesService(self.store)
        return service.delete_message(message_id)

