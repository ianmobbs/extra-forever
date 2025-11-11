"""
Messages controller for handling CLI and API requests.
"""
import tempfile
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel

from app.services.messages_service import MessagesService, ImportOptions, ImportResult
from app.stores.sqlite_store import SQLiteStore


class MessageResponse(BaseModel):
    """API response model for a message preview."""
    id: str
    subject: str
    sender: str
    snippet: str | None


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
                    snippet=msg.snippet
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

