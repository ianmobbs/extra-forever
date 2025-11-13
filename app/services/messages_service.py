"""
Messages service for orchestrating message import and processing.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.managers.message_manager import MessageManager
from app.services.embedding_service import EmbeddingService
from app.stores.sqlite_store import SQLiteStore
from app.utils.jsonl_parser import (
    decode_base64_body,
    extract_text_from_html,
    is_html,
    parse_iso_date,
)
from models import Message

if TYPE_CHECKING:
    from app.services.classification import ClassificationService

logger = logging.getLogger(__name__)


@dataclass
class ClassificationOptions:
    """Options for message classification."""

    auto_classify: bool = False
    top_n: int = 3
    threshold: float = 0.5


@dataclass
class ImportResult:
    """Result of a message import operation."""

    total_imported: int
    preview_messages: list[Message]


@dataclass
class ImportOptions:
    """Options for message import."""

    drop_existing: bool = True
    classification: ClassificationOptions | None = None

    def __post_init__(self):
        if self.classification is None:
            self.classification = ClassificationOptions()


@dataclass
class MessageResult:
    """Result of a message operation."""

    message: Message


class MessagesService:
    """Service for orchestrating message import and processing operations."""

    def __init__(
        self,
        db_session: Session,
        embedding_service: EmbeddingService | None = None,
        classification_service: ClassificationService | None = None,
        store: SQLiteStore | None = None,
    ):
        self.db_session = db_session
        self.embedding_service = embedding_service or EmbeddingService()
        self.classification_service = classification_service
        self.store = store  # Only needed for import_from_jsonl to call init_db

    @staticmethod
    def parse_message_content(content: str, is_base64_encoded: bool = False) -> str:
        """
        Parse and normalize message content.

        This method centralizes all message content parsing:
        1. Decodes base64 if needed
        2. Extracts plain text from HTML if content contains HTML

        Args:
            content: The message content (may be base64-encoded or plain text)
            is_base64_encoded: Whether the content is base64-encoded

        Returns:
            Normalized plain text content
        """
        # Step 1: Decode base64 if needed
        if is_base64_encoded:
            content = decode_base64_body(content)

        # Step 2: Extract text from HTML if content is HTML
        if content and is_html(content):
            content = extract_text_from_html(content)

        return content

    def import_from_jsonl(self, file_path: Path, options: ImportOptions) -> ImportResult:
        """
        Import messages from a JSONL file.

        Note: This method requires a store to be passed during initialization for DB init.

        Args:
            file_path: Path to the JSONL file
            options: Import configuration options

        Returns:
            ImportResult with count and preview messages
        """
        if not self.store:
            raise ValueError("Store required for import_from_jsonl operation")

        # Initialize database
        self.store.init_db(drop_existing=options.drop_existing)

        # Parse messages from file
        messages = self._parse_jsonl_file(file_path)

        # Store messages using a new session for the import transaction
        import_session = self.store.create_session()
        try:
            manager = MessageManager(import_session)
            manager.bulk_create(messages)
            import_session.commit()

            # Get preview
            preview = manager.get_first_n(5)

            # Auto-classify messages if requested
            if options.classification and options.classification.auto_classify:
                self._classify_all_messages(
                    messages,
                    top_n=options.classification.top_n,
                    threshold=options.classification.threshold,
                )

            return ImportResult(total_imported=len(messages), preview_messages=preview)
        finally:
            import_session.close()

    def _parse_jsonl_file(self, file_path: Path) -> list[Message]:
        """Parse JSONL file and convert to Message objects."""
        from app.utils.jsonl_parser import parse_jsonl

        def parse_message(data: dict) -> Message:
            # Parse and normalize message body (base64 decode + HTML text extraction)
            body_content = self.parse_message_content(data["body"], is_base64_encoded=True)

            # Parse date using utility function
            date_obj = parse_iso_date(data["date"])

            message = Message(
                id=data["id"],
                subject=data["subject"],
                sender=data["from"],
                to=data["to"],
                snippet=data.get("snippet"),
                body=body_content,
                date=date_obj,
            )

            # Generate embedding for the message
            message.embedding = self.embedding_service.embed_message(message)

            return message

        return parse_jsonl(file_path, parse_message)

    def _classify_all_messages(self, messages: list[Message], top_n: int, threshold: float) -> None:
        """
        Classify all messages and assign them to categories.

        Requires a classification service to be injected during initialization.

        Args:
            messages: List of messages to classify
            top_n: Maximum number of categories per message
            threshold: Minimum similarity threshold

        Raises:
            ValueError: If no classification service was injected
        """
        if self.classification_service is None:
            raise ValueError(
                "Classification service must be injected to use auto-classification. "
                "Pass a ClassificationService instance during MessagesService initialization."
            )

        # Run async classification in a sync context
        asyncio.run(self._classify_all_messages_async(messages))

    async def _classify_all_messages_async(self, messages: list[Message]) -> None:
        """Async helper for classifying all messages."""
        if self.classification_service is None:
            return

        for message in messages:
            # Skip messages that can't be classified (e.g., no categories available)
            with suppress(ValueError):
                # Classify message (which also assigns categories)
                await self.classification_service.classify_message_by_id(message.id)

    def create_message(
        self,
        id: str,
        subject: str,
        sender: str,
        to: list[str],
        snippet: str | None = None,
        body: str | None = None,
        date: datetime | None = None,
        body_is_base64_encoded: bool = False,
    ) -> MessageResult:
        """
        Create a new message.

        Args:
            id: Unique message ID
            subject: Message subject
            sender: Sender email
            to: List of recipient emails
            snippet: Short preview text
            body: Full message body (may be base64-encoded, will be processed for HTML extraction)
            date: Message date
            body_is_base64_encoded: Whether the body is base64-encoded

        Returns:
            MessageResult with the created message
        """
        start_time = time.time()
        logger.debug(f"Creating message: {id[:20]}... subject='{subject[:50]}...'")

        # Parse and normalize body content (base64 decode + extract text from HTML if needed)
        if body:
            body = self.parse_message_content(body, is_base64_encoded=body_is_base64_encoded)

        # Create temporary message object for embedding
        temp_message = Message(
            id=id, subject=subject, sender=sender, to=to, snippet=snippet, body=body, date=date
        )

        # Generate embedding
        embedding = self.embedding_service.embed_message(temp_message)

        manager = MessageManager(self.db_session)
        try:
            message = manager.create(
                id=id,
                subject=subject,
                sender=sender,
                to=to,
                snippet=snippet,
                body=body,
                date=date,
                embedding=embedding,
            )
            self.db_session.commit()
            self.db_session.refresh(message)
            logger.debug(f"Message created in {time.time() - start_time:.3f}s")
            return MessageResult(message=message)
        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(f"Message with id '{id}' already exists")
            raise ValueError(f"Message with id '{id}' already exists") from e
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create message {id}: {e}")
            raise

    def get_message(self, message_id: str) -> MessageResult | None:
        """
        Get a message by ID.

        Args:
            message_id: Message ID

        Returns:
            MessageResult or None if not found
        """
        manager = MessageManager(self.db_session)
        message = manager.get_by_id(message_id)
        if message:
            return MessageResult(message=message)
        return None

    def list_messages(self, limit: int | None = None, offset: int | None = None) -> list[Message]:
        """
        List all messages with optional pagination.

        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of messages
        """
        manager = MessageManager(self.db_session)
        return manager.get_all(limit=limit, offset=offset)

    def update_message(
        self,
        message_id: str,
        subject: str | None = None,
        sender: str | None = None,
        to: list[str] | None = None,
        snippet: str | None = None,
        body: str | None = None,
        date: datetime | None = None,
    ) -> MessageResult | None:
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
        manager = MessageManager(self.db_session)

        # Get existing message to build updated version for embedding
        existing_message = manager.get_by_id(message_id)
        if not existing_message:
            return None

        try:
            # Build updated message object for embedding generation
            temp_message = Message(
                id=message_id,
                subject=subject if subject is not None else existing_message.subject,
                sender=sender if sender is not None else existing_message.sender,
                to=to if to is not None else existing_message.to,
                snippet=snippet if snippet is not None else existing_message.snippet,
                body=body if body is not None else existing_message.body,
                date=date if date is not None else existing_message.date,
            )

            # Regenerate embedding with updated data (idempotent with create)
            embedding = self.embedding_service.embed_message(temp_message)

            message = manager.update(
                message_id,
                subject=subject,
                sender=sender,
                to=to,
                snippet=snippet,
                body=body,
                date=date,
                embedding=embedding,
            )
            if message:
                self.db_session.commit()
                self.db_session.refresh(message)
                return MessageResult(message=message)
            return None
        except Exception:
            self.db_session.rollback()
            raise

    def delete_message(self, message_id: str) -> bool:
        """
        Delete a message.

        Args:
            message_id: Message ID

        Returns:
            True if deleted, False if not found
        """
        manager = MessageManager(self.db_session)
        try:
            result = manager.delete(message_id)
            if result:
                self.db_session.commit()
            return result
        except Exception:
            self.db_session.rollback()
            raise
