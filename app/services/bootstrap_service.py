"""
Bootstrap service for initializing the system with sample data.
"""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.services.categories_service import CategoriesService
from app.services.messages_service import ClassificationOptions, MessagesService
from app.stores.sqlite_store import SQLiteStore
from models import Category, Message


@dataclass
class BootstrapResult:
    """Result of a bootstrap operation."""

    total_categories: int
    total_messages: int
    total_classified: int
    preview_messages: list[Message]
    preview_categories: list[Category]


class BootstrapService:
    """Service for bootstrapping the system with initial data."""

    def __init__(self, store: SQLiteStore):
        self.store = store
        self.messages_service = MessagesService(store)
        self.categories_service = CategoriesService(store)

    def bootstrap(
        self,
        messages_file: Path | None = None,
        categories_file: Path | None = None,
        drop_existing: bool = True,
        classification_options: ClassificationOptions | None = None,
    ) -> BootstrapResult:
        """
        Bootstrap the system with messages and categories.

        Args:
            messages_file: Path to JSONL file with messages
            categories_file: Path to JSONL file with categories
            drop_existing: Whether to drop existing tables
            classification_options: Options for automatic classification

        Returns:
            BootstrapResult with import statistics
        """
        # Initialize database
        self.store.init_db(drop_existing=drop_existing)

        # Bootstrap categories first
        categories = []
        if categories_file and categories_file.exists():
            categories = self._bootstrap_categories(categories_file)

        # Bootstrap messages
        messages = []
        if messages_file and messages_file.exists():
            messages = self._bootstrap_messages(messages_file)

        # Auto-classify messages if requested and we have categories
        total_classified = 0
        if (
            classification_options
            and classification_options.auto_classify
            and categories
            and messages
        ):
            total_classified = self._classify_messages(
                [msg.id for msg in messages], classification_options
            )

        # Re-fetch preview messages to get updated categories
        preview_messages = messages[:5]
        if total_classified > 0 and preview_messages:
            # Refresh messages from database to get categories
            from app.managers.message_manager import MessageManager

            session = self.store.create_session()
            try:
                manager = MessageManager(session)
                # Get the first N messages with categories
                preview_messages = manager.get_first_n(5)
            finally:
                session.close()

        return BootstrapResult(
            total_categories=len(categories),
            total_messages=len(messages),
            total_classified=total_classified,
            preview_messages=preview_messages,
            preview_categories=categories[:5],
        )

    def _bootstrap_categories(self, file_path: Path) -> list[Category]:
        """
        Bootstrap categories from JSONL file.

        Each line should have: {"name": "...", "description": "..."}
        """
        categories = []

        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                result = self.categories_service.create_category(
                    name=data["name"], description=data["description"]
                )
                categories.append(result.category)

        return categories

    def _bootstrap_messages(self, file_path: Path) -> list[Message]:
        """
        Bootstrap messages from JSONL file.

        Each line should have Gmail-style message format.
        """
        messages = []

        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)

                # Decode body
                body_decoded = base64.b64decode(data["body"]).decode("utf-8", errors="replace")

                # Parse date
                date_obj = datetime.fromisoformat(data["date"].replace("Z", "+00:00"))

                # Create message using the service (which generates embedding)
                result = self.messages_service.create_message(
                    id=data["id"],
                    subject=data["subject"],
                    sender=data["from"],
                    to=data["to"],
                    snippet=data.get("snippet"),
                    body=body_decoded,
                    date=date_obj,
                )
                messages.append(result.message)

        return messages

    def _classify_messages(
        self, message_ids: list[str], classification_options: ClassificationOptions
    ) -> int:
        """
        Classify a batch of messages.

        Returns the number of successfully classified messages.
        """
        from app.services.classification_service import ClassificationService

        classification_service = ClassificationService(
            self.store,
            top_n=classification_options.top_n,
            threshold=classification_options.threshold,
        )

        classified_count = 0
        for message_id in message_ids:
            try:
                classification_service.classify_message(message_id)
                classified_count += 1
            except ValueError:
                # Skip messages that can't be classified
                pass

        return classified_count
