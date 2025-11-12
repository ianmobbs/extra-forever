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
    """Output schema for LLM classification of a single category."""

    category_index: int  # 0-based index of the category in the provided list
    is_in_category: bool
    explanation: str
    confidence: float  # 0.0 to 1.0 confidence score


class MultiCategoryMatchOutput(BaseModel):
    """Output schema for LLM classification of multiple categories at once."""

    matches: list[CategoryMatchOutput]


class LLMClassificationStrategy(ClassificationStrategy):
    """
    Classification strategy using an LLM (Language Model) via pydantic-ai.

    This strategy sends the message content and all category descriptions to an LLM
    and asks it to determine which categories the message belongs to in a single request.

    Unlike embedding-based strategies, this provides:
    - Deep semantic understanding of message content
    - Natural language explanations for classification decisions
    - Ability to reason about context and intent

    Optimization: Makes O(M) requests instead of O(M*N) by evaluating all categories
    for a message in a single LLM call.
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
            output_type=MultiCategoryMatchOutput,
            instructions=(
                "You are an email classification assistant. "
                "Given an email message and a list of category descriptions, determine which "
                "categories the email belongs in. For each category, provide a boolean match, "
                "a confidence score (0.0 to 1.0), and an explanation. Be precise and consider "
                "the semantic meaning of both the category descriptions and the email content. "
                "You must evaluate ALL categories provided and return a match result for each one."
            ),
        )

    def classify(
        self, message: Message, categories: list[Category], top_n: int, threshold: float
    ) -> list[ClassificationMatch]:
        """
        Classify using an LLM to determine category membership.

        The LLM evaluates all categories in a single request, returning matches with
        confidence scores and explanations.

        Args:
            message: Message to classify (doesn't require embedding)
            categories: List of categories to match against
            top_n: Maximum number of matches to return
            threshold: Minimum confidence score (0-1) to include a match

        Returns:
            List of ClassificationMatch objects for categories the LLM matched,
            sorted by confidence score in descending order

        Note:
            - This method makes a single LLM call to evaluate all categories (O(M) instead of O(M*N))
            - The confidence scores from the LLM are used directly as scores
            - Only matches with is_in_category=True and confidence >= threshold are returned
        """
        if not categories:
            return []

        # Build a rich text representation of the message
        message_text = self._build_message_text(message)

        # Build the prompt with all categories
        prompt = self._build_multi_category_prompt(message_text, categories)

        # Call the LLM agent once with all categories
        result = self._agent.run_sync(prompt)
        output: MultiCategoryMatchOutput = result.output

        # Process all matches from the LLM
        matches: list[ClassificationMatch] = []
        for match_output in output.matches:
            # Only include if the LLM says it's a match, meets threshold, and has valid index
            if (
                match_output.is_in_category
                and match_output.confidence >= threshold
                and 0 <= match_output.category_index < len(categories)
            ):
                category = categories[match_output.category_index]
                matches.append(
                    ClassificationMatch(
                        category=category,
                        score=match_output.confidence,
                        explanation=match_output.explanation,
                    )
                )

        # Sort by confidence score descending
        matches.sort(key=lambda m: m.score, reverse=True)

        # Return top_n matches
        return matches[:top_n]

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

    def _build_multi_category_prompt(self, message_text: str, categories: list[Category]) -> str:
        """
        Build the prompt for classifying a message against multiple categories.

        Args:
            message_text: Formatted message text
            categories: List of categories to evaluate

        Returns:
            Prompt string for the LLM
        """
        # Build the categories list with 0-based indices
        categories_text = []
        for i, category in enumerate(categories):
            categories_text.append(f"[{i}] {category.name}")
            categories_text.append(f"    Description: {category.description}")

        categories_str = "\n".join(categories_text)

        return f"""
I need you to determine which of the following categories this email belongs to.
Evaluate EACH category and provide a match result for ALL of them.

Categories (with 0-based indices):
{categories_str}

Email:
{message_text}

For each category, determine:
1. The category_index (0-based index from the list above, e.g., 0, 1, 2, etc.)
2. Whether the email belongs in that category (is_in_category: true/false)
3. Your confidence in that determination (confidence: 0.0 to 1.0)
4. A brief explanation of your reasoning

IMPORTANT: Use the numeric index (0, 1, 2, etc.) for category_index, NOT the category name.
Evaluate ALL {len(categories)} categories listed above.
"""
