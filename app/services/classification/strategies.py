"""
Classification strategies for categorizing messages.

This module contains pure classification logic that doesn't know about persistence.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel
from pydantic_ai import Agent

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


class CategoryMatchOutput(BaseModel):
    """Output schema for LLM classification of a message against a category."""

    is_in_category: bool
    explanation: str


class LLMClassificationStrategy(ClassificationStrategy):
    """
    Classification strategy using an LLM (Language Model) via pydantic-ai.

    This strategy sends the message content and category description to an LLM
    and asks it to determine if the message belongs in that category.

    Unlike embedding-based strategies, this provides:
    - Deep semantic understanding of message content
    - Natural language explanations for classification decisions
    - Ability to reason about context and intent

    Note: This strategy is slower and more expensive than embedding-based approaches
    since it requires an LLM API call for each message-category pair.
    """

    def __init__(self, model: str = "openai:gpt-4o-mini"):
        """
        Initialize the LLM classification strategy.

        Args:
            model: Model identifier for pydantic-ai (e.g., "openai:gpt-4o-mini")
        """
        self.model = model
        self._agent = Agent(
            model=self.model,
            output_type=CategoryMatchOutput,
            instructions=(
                "You are an email classification assistant. "
                "Given an email message and a category description, determine if the email "
                "belongs in that category. Be precise and consider the semantic meaning "
                "of both the category description and the email content."
            ),
        )

    def classify(
        self, message: Message, categories: list[Category], top_n: int, threshold: float
    ) -> list[ClassificationMatch]:
        """
        Classify using an LLM to determine category membership.

        For each category, the LLM evaluates whether the message belongs in it.
        Matched categories receive a score of 1.0, non-matches receive 0.0.

        Args:
            message: Message to classify (doesn't require embedding)
            categories: List of categories to match against
            top_n: Maximum number of matches to return
            threshold: Minimum score (0-1) - typically 0.5 or 1.0 for LLM classification

        Returns:
            List of ClassificationMatch objects for categories the LLM matched

        Note:
            - This method makes synchronous LLM calls for each category
            - The threshold parameter is respected but LLM scoring is binary (0.0 or 1.0)
            - Set threshold <= 0.5 to require matches, > 0.5 for stricter matching
        """
        if not categories:
            return []

        # Build a rich text representation of the message
        message_text = self._build_message_text(message)

        matches: list[ClassificationMatch] = []

        # Evaluate each category until we have enough matches
        for category in categories:
            # Stop early if we have enough matches
            if len(matches) >= top_n:
                break

            # Build the prompt for this category
            prompt = self._build_classification_prompt(message_text, category)

            # Call the LLM agent
            result = self._agent.run_sync(prompt)
            output: CategoryMatchOutput = result.output

            # If the LLM says it's a match, add it to results
            if output.is_in_category:
                score = 1.0
                # Only include if it meets the threshold
                if score >= threshold:
                    matches.append(
                        ClassificationMatch(
                            category=category, score=score, explanation=output.explanation
                        )
                    )

        return matches

    def _build_message_text(self, message: Message) -> str:
        """
        Build a rich text representation of the message for LLM analysis.

        Args:
            message: Message to represent

        Returns:
            Formatted string with message details
        """
        parts = []

        if message.subject:
            parts.append(f"Subject: {message.subject}")

        if message.sender:
            parts.append(f"From: {message.sender}")

        if message.to:
            # Handle list of recipients
            to_str = message.to if isinstance(message.to, str) else ", ".join(message.to)
            parts.append(f"To: {to_str}")

        if message.date:
            parts.append(f"Date: {message.date}")

        if message.snippet:
            parts.append(f"Preview: {message.snippet}")

        if message.body:
            # Truncate very long bodies to avoid token limits
            body_text = message.body
            if len(body_text) > 5000:
                body_text = body_text[:5000] + "... (truncated)"
            parts.append(f"Body: {body_text}")

        return "\n".join(parts)

    def _build_classification_prompt(self, message_text: str, category: Category) -> str:
        """
        Build the prompt for classifying a message against a category.

        Args:
            message_text: Formatted message text
            category: Category to evaluate

        Returns:
            Prompt string for the LLM
        """
        return f"""
I need you to determine if the following email belongs in this category:

Category: {category.name}
Description: {category.description}

Email:
{message_text}

Does this email belong in the "{category.name}" category?
"""
