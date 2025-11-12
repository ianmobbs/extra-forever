"""
Classification strategies for categorizing messages.

This module contains pure classification logic that doesn't know about persistence.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from models import Category, Message


@dataclass
class ClassificationMatch:
    """A single classification match result."""

    category: Category
    score: float
    explanation: str


class ClassificationStrategy(ABC):
    """Base class for classification strategies."""

    @abstractmethod
    def classify(
        self, message: Message, categories: list[Category], top_n: int, threshold: float
    ) -> list[ClassificationMatch]:
        """
        Classify a message against a list of categories.

        Args:
            message: Message to classify (must have embedding)
            categories: List of categories to match against (must have embeddings)
            top_n: Maximum number of matches to return
            threshold: Minimum score threshold

        Returns:
            List of ClassificationMatch objects, sorted by score descending
        """
        pass


class EmbeddingSimilarityStrategy(ClassificationStrategy):
    """Classification strategy using cosine similarity of embeddings."""

    def classify(
        self, message: Message, categories: list[Category], top_n: int, threshold: float
    ) -> list[ClassificationMatch]:
        """
        Classify using cosine similarity between message and category embeddings.

        Args:
            message: Message with embedding
            categories: List of categories with embeddings
            top_n: Maximum number of matches to return
            threshold: Minimum cosine similarity score (0-1)

        Returns:
            List of ClassificationMatch objects

        Raises:
            ValueError: If message or any category lacks an embedding
        """
        if not message.embedding:
            raise ValueError(f"Message {message.id} has no embedding")

        # Filter categories with embeddings
        categories_with_embeddings = [cat for cat in categories if cat.embedding]
        if not categories_with_embeddings:
            return []

        # Convert message embedding to numpy array
        message_vec = np.array(message.embedding)

        # Build category embedding matrix
        category_vecs = np.array([cat.embedding for cat in categories_with_embeddings])

        # Compute cosine similarity using matrix multiplication
        # cosine_sim = (A · B) / (||A|| * ||B||)
        # We normalize the vectors first, then dot product
        message_norm = message_vec / np.linalg.norm(message_vec)
        category_norms = category_vecs / np.linalg.norm(category_vecs, axis=1, keepdims=True)

        # Compute similarities via matrix multiplication
        similarities = category_norms @ message_norm

        # Get indices sorted by similarity (descending)
        sorted_indices = np.argsort(similarities)[::-1]

        # Filter by threshold and top_n
        matches: list[ClassificationMatch] = []

        for idx in sorted_indices:
            if similarities[idx] >= threshold and len(matches) < top_n:
                category = categories_with_embeddings[idx]
                score = float(similarities[idx])
                explanation = (
                    f"Message {message.id} embeddings exceed {threshold:.2f} "
                    f"similarity threshold for category '{category.name}' with score {score:.4f}"
                )
                matches.append(
                    ClassificationMatch(category=category, score=score, explanation=explanation)
                )

        return matches
