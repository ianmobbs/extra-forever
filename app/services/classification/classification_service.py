"""
Classification service for categorizing messages.

This service orchestrates the classification process:
1. Fetching message and categories from persistence
2. Running classification strategy (pure logic)
3. Persisting category assignments
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC

from sqlalchemy.orm import Session

from app.managers.category_manager import CategoryManager
from app.managers.message_manager import MessageManager
from app.services.classification.strategies import (
    ClassificationStrategy,
    EmbeddingSimilarityStrategy,
)
from models import Category, Message

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of a classification operation."""

    message: Message
    matched_categories: list[Category]
    scores: list[float]  # Cosine similarity scores for each matched category
    explanations: list[str]  # Plain-English explanations for each match


class ClassificationService:
    """Service for classifying messages into categories."""

    def __init__(
        self,
        db_session: Session,
        strategy: ClassificationStrategy | None = None,
        top_n: int = 3,
        threshold: float = 0.5,
    ):
        """
        Initialize the classification service.

        Args:
            db_session: Database session for accessing messages and categories
            strategy: Classification strategy to use (defaults to EmbeddingSimilarityStrategy)
            top_n: Maximum number of categories to return
            threshold: Minimum score to include a category (0-1)
        """
        self.db_session = db_session
        self.strategy = strategy or EmbeddingSimilarityStrategy()
        self.top_n = top_n
        self.threshold = threshold

    def classify_message(
        self, message: Message, categories: list[Category], assign: bool = True
    ) -> ClassificationResult:
        """
        Classify a message into categories.

        Args:
            message: Message to classify (must have embedding)
            categories: List of categories to match against
            assign: Whether to persist category assignments to the database

        Returns:
            ClassificationResult with matched categories and scores

        Raises:
            ValueError: If message has no embedding
            ValueError: If no categories have embeddings
        """
        start_time = time.time()
        logger.debug(f"Classifying message {message.id} against {len(categories)} categories")

        if not message.embedding:
            logger.warning(f"Message {message.id} has no embedding")
            raise ValueError(f"Message {message.id} has no embedding")

        # Filter to categories with embeddings
        categories_with_embeddings = [cat for cat in categories if cat.embedding]
        if not categories_with_embeddings:
            logger.warning("No categories with embeddings found")
            raise ValueError("No categories with embeddings found")

        if len(categories_with_embeddings) < len(categories):
            logger.debug(
                f"Filtered to {len(categories_with_embeddings)}/{len(categories)} categories with embeddings"
            )

        # Run classification strategy (pure logic)
        matches = self.strategy.classify(
            message=message,
            categories=categories_with_embeddings,
            top_n=self.top_n,
            threshold=self.threshold,
        )

        # Extract results
        matched_categories = [match.category for match in matches]
        scores = [match.score for match in matches]
        explanations = [match.explanation for match in matches]

        logger.debug(
            f"Classification found {len(matched_categories)} matches in {time.time() - start_time:.3f}s"
        )

        # Optionally persist assignments
        if assign:
            logger.debug(f"Persisting {len(matched_categories)} category assignments")
            self._assign_categories(
                message.id,
                [
                    (cat.id, score, explanation)
                    for cat, score, explanation in zip(
                        matched_categories, scores, explanations, strict=True
                    )
                ],
            )

        return ClassificationResult(
            message=message,
            matched_categories=matched_categories,
            scores=scores,
            explanations=explanations,
        )

    def classify_message_by_id(self, message_id: str, assign: bool = True) -> ClassificationResult:
        """
        Classify a message by ID (fetches message and categories from DB).

        Args:
            message_id: ID of the message to classify
            assign: Whether to persist category assignments to the database

        Returns:
            ClassificationResult with matched categories and scores

        Raises:
            ValueError: If message not found
        """
        logger.debug(f"Fetching message and categories for classification: {message_id}")
        message_manager = MessageManager(self.db_session)
        category_manager = CategoryManager(self.db_session)

        # Get the message
        message = message_manager.get_by_id(message_id)
        if not message:
            logger.error(f"Message with ID {message_id} not found")
            raise ValueError(f"Message with ID {message_id} not found")

        # Get all categories
        categories = category_manager.get_all()
        logger.debug(f"Found {len(categories)} categories for classification")

        # Classify using the main method
        return self.classify_message(message=message, categories=categories, assign=assign)

    def _assign_categories(
        self, message_id: str, classifications: list[tuple[int, float, str]]
    ) -> None:
        """
        Persist category assignments with metadata to the database.

        Args:
            message_id: Message ID
            classifications: List of tuples (category_id, score, explanation)
        """
        from datetime import datetime

        from models import MessageCategory

        message_manager = MessageManager(self.db_session)

        message = message_manager.get_by_id(message_id)
        if message:
            # Clear existing message_categories associations
            for mc in message.message_categories:
                self.db_session.delete(mc)

            # Create new associations with metadata
            for category_id, score, explanation in classifications:
                message_category = MessageCategory(
                    message_id=message_id,
                    category_id=category_id,
                    score=score,
                    explanation=explanation,
                    classified_at=datetime.now(UTC),
                )
                self.db_session.add(message_category)

            self.db_session.commit()
