"""
Bootstrap service for initializing the system with sample data.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from app.services.categories_service import CategoriesService
from app.services.messages_service import ClassificationOptions, MessagesService
from app.stores.sqlite_store import SQLiteStore
from app.utils.jsonl_parser import parse_iso_date
from models import Category, Message

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        store: SQLiteStore,
        messages_service: MessagesService,
        categories_service: CategoriesService,
    ):
        self.store = store
        self.messages_service = messages_service
        self.categories_service = categories_service

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
        start_time = time.time()
        logger.info("Starting bootstrap process")
        logger.info(
            f"Parameters: messages_file={messages_file}, categories_file={categories_file}, "
            f"drop_existing={drop_existing}, auto_classify={classification_options.auto_classify if classification_options else False}"
        )

        # Initialize database
        db_start = time.time()
        logger.info("Initializing database...")
        self.store.init_db(drop_existing=drop_existing)
        logger.info(f"Database initialized in {time.time() - db_start:.2f}s")

        # Bootstrap categories first
        categories = []
        if categories_file and categories_file.exists():
            logger.info(f"Bootstrapping categories from {categories_file}")
            categories = self._bootstrap_categories(categories_file)
            logger.info(f"Loaded {len(categories)} categories")
        else:
            logger.warning(f"Categories file not found or not specified: {categories_file}")

        # Bootstrap messages
        messages = []
        if messages_file and messages_file.exists():
            logger.info(f"Bootstrapping messages from {messages_file}")
            messages = self._bootstrap_messages(messages_file)
            logger.info(f"Loaded {len(messages)} messages")
        else:
            logger.warning(f"Messages file not found or not specified: {messages_file}")

        # Auto-classify messages if requested and we have categories
        total_classified = 0
        if (
            classification_options
            and classification_options.auto_classify
            and categories
            and messages
        ):
            logger.info(
                f"Starting classification with top_n={classification_options.top_n}, "
                f"threshold={classification_options.threshold}"
            )
            total_classified = self._classify_messages(
                [msg.id for msg in messages], classification_options
            )
            logger.info(f"Classified {total_classified} messages")

        # Re-fetch preview messages to get updated categories
        preview_messages = messages[:5]
        if total_classified > 0 and preview_messages:
            logger.debug("Refreshing preview messages from database")
            # Refresh messages from database to get categories
            from app.managers.message_manager import MessageManager

            session = self.store.create_session()
            try:
                manager = MessageManager(session)
                # Get the first N messages with categories
                preview_messages = manager.get_first_n(5)
            finally:
                session.close()

        total_time = time.time() - start_time
        logger.info(
            f"Bootstrap completed in {total_time:.2f}s: "
            f"{len(categories)} categories, {len(messages)} messages, {total_classified} classified"
        )

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
        start_time = time.time()
        from app.utils.jsonl_parser import parse_jsonl

        def parse_category(data: dict) -> Category:
            logger.debug(f"Creating category: {data.get('name', 'unknown')}")
            result = self.categories_service.create_category(
                name=data["name"], description=data["description"]
            )
            return result.category

        categories = parse_jsonl(file_path, parse_category)
        logger.info(f"Categories bootstrap took {time.time() - start_time:.2f}s")
        return categories

    def _bootstrap_messages(self, file_path: Path) -> list[Message]:
        """
        Bootstrap messages from JSONL file.

        Each line should have Gmail-style message format.
        """
        start_time = time.time()
        from app.utils.jsonl_parser import parse_jsonl

        message_count = [0]  # Use list to allow mutation in nested function

        def parse_message(data: dict) -> Message:
            message_count[0] += 1
            if message_count[0] % 10 == 0:
                logger.debug(
                    f"Processing message {message_count[0]}: {data.get('subject', 'unknown')[:50]}"
                )
            # Parse date using utility function
            date_obj = parse_iso_date(data["date"])

            # Create message using the service (which handles base64 decoding, HTML extraction, and embedding)
            result = self.messages_service.create_message(
                id=data["id"],
                subject=data["subject"],
                sender=data["from"],
                to=data["to"],
                snippet=data.get("snippet"),
                body=data["body"],  # Pass raw base64-encoded body
                date=date_obj,
                body_is_base64_encoded=True,  # Let the service handle decoding and parsing
            )
            return result.message

        messages = parse_jsonl(file_path, parse_message)
        logger.info(f"Messages bootstrap took {time.time() - start_time:.2f}s")
        return messages

    def _classify_messages(
        self, message_ids: list[str], classification_options: ClassificationOptions
    ) -> int:
        """
        Classify a batch of messages.

        Returns the number of successfully classified messages.
        """
        start_time = time.time()
        from app.services.classification import ClassificationService, LLMClassificationStrategy

        logger.info(f"Classifying {len(message_ids)} messages using LLM strategy")
        # Create a new session for classification batch operation
        session = self.store.create_session()
        try:
            # Use LLM strategy for classification
            llm_strategy = LLMClassificationStrategy(model="openai:gpt-4o-mini")
            classification_service = ClassificationService(
                session,
                strategy=llm_strategy,
                top_n=classification_options.top_n,
                threshold=classification_options.threshold,
            )

            classified_count = 0
            for idx, message_id in enumerate(message_ids, 1):
                try:
                    if idx % 5 == 0:
                        logger.debug(f"Classifying message {idx}/{len(message_ids)}")
                    classification_service.classify_message_by_id(message_id)
                    classified_count += 1
                except ValueError as e:
                    logger.warning(f"Failed to classify message {message_id}: {e}")
                    # Skip messages that can't be classified
                    pass

            elapsed = time.time() - start_time
            logger.info(
                f"Classification completed in {elapsed:.2f}s ({elapsed / len(message_ids):.2f}s per message)"
            )
            return classified_count
        finally:
            session.close()
