"""
Messages controller for handling CLI and API requests.
"""

import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.classification_service import ClassificationResult, ClassificationService
from app.services.messages_service import (
    ClassificationOptions,
    ImportOptions,
    ImportResult,
    MessagesService,
)
from app.stores.sqlite_store import SQLiteStore


class CategoryInMessage(BaseModel):
    """Category info in message response."""

    id: int
    name: str
    description: str


class MessageResponse(BaseModel):
    """API response model for a message."""

    id: str
    subject: str
    sender: str
    to: list[str]
    snippet: str | None = None
    body: str | None = None
    date: datetime | None = None
    categories: list[CategoryInMessage] = []


class MessageCreateRequest(BaseModel):
    """API request model for creating a message."""

    id: str
    subject: str
    sender: str
    to: list[str]
    snippet: str | None = None
    body: str | None = None
    date: datetime | None = None


class MessageUpdateRequest(BaseModel):
    """API request model for updating a message."""

    subject: str | None = None
    sender: str | None = None
    to: list[str] | None = None
    snippet: str | None = None
    body: str | None = None
    date: datetime | None = None


class ImportResponse(BaseModel):
    """API response for import operation."""

    total_imported: int
    preview: list[MessageResponse]


class CategoryClassification(BaseModel):
    """Single category classification result."""

    category_id: int
    category_name: str
    is_in_category: bool = True  # Always true for matched categories
    explanation: str


class ClassifyResponse(BaseModel):
    """
    API response for classification operation.

    Returns classification results for a single message across multiple categories.
    """

    message_id: str
    classifications: list[CategoryClassification]


def _message_to_response(msg) -> MessageResponse:
    """Helper to convert a Message to MessageResponse with categories."""
    return MessageResponse(
        id=msg.id,
        subject=msg.subject,
        sender=msg.sender,
        to=msg.to,
        snippet=msg.snippet,
        body=msg.body,
        date=msg.date,
        categories=[
            CategoryInMessage(id=cat.id, name=cat.name, description=cat.description)
            for cat in msg.categories
        ],
    )


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
        self.router.get("/", response_model=list[MessageResponse])(self.list_messages_api)
        self.router.get("/{message_id}", response_model=MessageResponse)(self.get_message_api)
        self.router.put("/{message_id}", response_model=MessageResponse)(self.update_message_api)
        self.router.delete("/{message_id}")(self.delete_message_api)
        self.router.post("/{message_id}/classify", response_model=ClassifyResponse)(
            self.classify_message_api
        )

    async def import_upload(
        self,
        file: UploadFile = File(...),
        drop_existing: bool = Form(True),
        auto_classify: bool = Form(False),
        classification_top_n: int = Form(3),
        classification_threshold: float = Form(0.5),
    ) -> ImportResponse:
        """
        API endpoint: Handle file upload and import messages.

        Wraps the uploaded file in a tempfile, then delegates to import_messages.
        """
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".jsonl") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            classification_opts = ClassificationOptions(
                auto_classify=auto_classify,
                top_n=classification_top_n,
                threshold=classification_threshold,
            )
            options = ImportOptions(drop_existing=drop_existing, classification=classification_opts)
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
                    date=msg.date,
                )
                for msg in result.preview_messages
            ]

            return ImportResponse(total_imported=result.total_imported, preview=preview)
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def import_messages(self, file_path: Path, options: ImportOptions) -> ImportResult:
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
                date=request.date,
            )
            return _message_to_response(result.message)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    async def list_messages_api(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[MessageResponse]:
        """
        API endpoint: List all messages.
        """
        messages = self.list_messages(limit=limit, offset=offset)
        return [_message_to_response(msg) for msg in messages]

    async def get_message_api(self, message_id: str) -> MessageResponse:
        """
        API endpoint: Get a message by ID.
        """
        result = self.get_message(message_id)
        if not result:
            raise HTTPException(status_code=404, detail="Message not found")

        return _message_to_response(result.message)

    async def update_message_api(
        self, message_id: str, request: MessageUpdateRequest
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
                date=request.date,
            )
            if not result:
                raise HTTPException(status_code=404, detail="Message not found")

            return _message_to_response(result.message)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

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
        to: list[str],
        snippet: str | None = None,
        body: str | None = None,
        date: datetime | None = None,
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

    def list_messages(self, limit: int | None = None, offset: int | None = None):
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
        subject: str | None = None,
        sender: str | None = None,
        to: list[str] | None = None,
        snippet: str | None = None,
        body: str | None = None,
        date: datetime | None = None,
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

    async def classify_message_api(
        self, message_id: str, top_n: int = 3, threshold: float = 0.5
    ) -> ClassifyResponse:
        """
        API endpoint: Classify a message into categories using cosine similarity.

        Args:
            message_id: Message ID
            top_n: Maximum number of categories to return
            threshold: Minimum cosine similarity score (0-1)
        """
        try:
            result = self.classify_message(message_id, top_n=top_n, threshold=threshold)

            classifications = [
                CategoryClassification(
                    category_id=cat.id,
                    category_name=cat.name,
                    is_in_category=True,
                    explanation=explanation,
                )
                for cat, explanation in zip(
                    result.matched_categories, result.explanations, strict=True
                )
            ]

            return ClassifyResponse(
                message_id=result.message.id,
                classifications=classifications,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    def classify_message(
        self, message_id: str, top_n: int = 3, threshold: float = 0.5
    ) -> ClassificationResult:
        """
        Classify a message into categories using cosine similarity.

        Categories are automatically assigned to the message.

        Args:
            message_id: Message ID
            top_n: Maximum number of categories to return
            threshold: Minimum cosine similarity score (0-1)

        Returns:
            ClassificationResult with matched categories and scores
        """
        service = ClassificationService(self.store, top_n=top_n, threshold=threshold)
        return service.classify_message(message_id)
