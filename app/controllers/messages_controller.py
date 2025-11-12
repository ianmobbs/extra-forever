"""
Messages controller for handling API requests.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import config
from app.deps import get_db_session, get_messages_service
from app.services.classification import ClassificationService
from app.services.messages_service import (
    ClassificationOptions,
    ImportOptions,
    MessagesService,
)

logger = logging.getLogger(__name__)


class CategoryInMessage(BaseModel):
    """Category info in message response with classification metadata."""

    id: int
    name: str
    description: str
    score: float | None = None  # Classification confidence score
    explanation: str | None = None  # Classification explanation
    classified_at: datetime | None = None  # When the classification was made


class MessageResponse(BaseModel):
    """API response model for a message."""

    id: str
    subject: str
    sender: str
    to: list[str]
    snippet: str | None = None
    body: str | None = None
    date: datetime | None = None
    categories: list[CategoryInMessage] = Field(default_factory=list)


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
    score: float  # Classification confidence score
    is_in_category: bool = True  # Always true for matched categories
    explanation: str


class ClassifyResponse(BaseModel):
    """API response for classification operation."""

    message_id: str
    classifications: list[CategoryClassification]


def _message_to_response(msg) -> MessageResponse:
    """Helper to convert a Message to MessageResponse with categories."""
    categories = []
    for mc in msg.message_categories:
        categories.append(
            CategoryInMessage(
                id=mc.category.id,
                name=mc.category.name,
                description=mc.category.description,
                score=mc.score,
                explanation=mc.explanation,
                classified_at=mc.classified_at,
            )
        )
    return MessageResponse(
        id=msg.id,
        subject=msg.subject,
        sender=msg.sender,
        to=msg.to,
        snippet=msg.snippet,
        body=msg.body,
        date=msg.date,
        categories=categories,
    )


class MessagesController:
    """Controller for message-related API operations."""

    def __init__(self):
        self.router = APIRouter(prefix="/messages", tags=["messages"])
        self._register_routes()

    def _register_routes(self):
        """Register FastAPI routes."""
        self.router.post("/import", response_model=ImportResponse)(self.import_upload)
        self.router.post("/", response_model=MessageResponse)(self.create_message)
        self.router.get("/", response_model=list[MessageResponse])(self.list_messages)
        self.router.get("/{message_id}", response_model=MessageResponse)(self.get_message)
        self.router.put("/{message_id}", response_model=MessageResponse)(self.update_message)
        self.router.delete("/{message_id}")(self.delete_message)
        self.router.post("/{message_id}/classify", response_model=ClassifyResponse)(
            self.classify_message
        )

    async def import_upload(
        self,
        file: UploadFile = File(...),
        drop_existing: bool = Form(True),
        auto_classify: bool = Form(False),
        classification_top_n: int = Form(config.CLASSIFICATION_TOP_N),
        classification_threshold: float = Form(config.CLASSIFICATION_THRESHOLD),
        service: MessagesService = Depends(get_messages_service),
    ) -> ImportResponse:
        """Import messages from uploaded JSONL file."""
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
            result = service.import_from_jsonl(Path(tmp_path), options)

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

    async def create_message(
        self,
        request: MessageCreateRequest,
        service: MessagesService = Depends(get_messages_service),
    ) -> MessageResponse:
        """Create a new message."""
        try:
            result = service.create_message(
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

    async def list_messages(
        self,
        limit: int | None = None,
        offset: int | None = None,
        service: MessagesService = Depends(get_messages_service),
    ) -> list[MessageResponse]:
        """List all messages."""
        messages = service.list_messages(limit=limit, offset=offset)
        return [_message_to_response(msg) for msg in messages]

    async def get_message(
        self, message_id: str, service: MessagesService = Depends(get_messages_service)
    ) -> MessageResponse:
        """Get a message by ID."""
        result = service.get_message(message_id)
        if not result:
            raise HTTPException(status_code=404, detail="Message not found")

        return _message_to_response(result.message)

    async def update_message(
        self,
        message_id: str,
        request: MessageUpdateRequest,
        service: MessagesService = Depends(get_messages_service),
    ) -> MessageResponse:
        """Update a message."""
        try:
            result = service.update_message(
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

    async def delete_message(
        self, message_id: str, service: MessagesService = Depends(get_messages_service)
    ):
        """Delete a message."""
        success = service.delete_message(message_id)
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")

        return {"message": "Message deleted successfully"}

    async def classify_message(
        self,
        message_id: str,
        top_n: int = Query(config.CLASSIFICATION_TOP_N, description="Maximum number of categories"),
        threshold: float = Query(
            config.CLASSIFICATION_THRESHOLD, description="Minimum similarity threshold"
        ),
        db_session: Session = Depends(get_db_session),
    ) -> ClassifyResponse:
        """Classify a message into categories using cosine similarity."""
        logger.info(f"Classifying message: {message_id} (top_n={top_n}, threshold={threshold})")
        try:
            # Create classification service with the requested top_n and threshold
            service = ClassificationService(db_session, top_n=top_n, threshold=threshold)
            result = service.classify_message_by_id(message_id)

            classifications = [
                CategoryClassification(
                    category_id=cat.id,
                    category_name=cat.name,
                    score=score,
                    is_in_category=True,
                    explanation=explanation,
                )
                for cat, score, explanation in zip(
                    result.matched_categories, result.scores, result.explanations, strict=True
                )
            ]

            return ClassifyResponse(
                message_id=result.message.id,
                classifications=classifications,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
