"""
Embedding service for generating text embeddings using OpenAI API.
"""

from openai import OpenAI

from app.config import config
from models import Category, Message


class EmbeddingService:
    """Service for generating embeddings using OpenAI's API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        Initialize the embedding service.

        Args:
            api_key: OpenAI API key (if None, will use config.OPENAI_API_KEY or OPENAI_API_KEY env var)
            model: Embedding model to use (if None, will use config.EMBEDDING_MODEL)
        """
        # Use provided api_key, or fall back to config, or let OpenAI client use env var
        key = api_key if api_key is not None else config.OPENAI_API_KEY
        self.client = OpenAI(api_key=key) if key else OpenAI()
        self.model = model if model is not None else config.EMBEDDING_MODEL

    def embed_message(self, message: Message) -> list[float]:
        """
        Generate an embedding for a message.

        Combines subject, sender, snippet, and body into a single text for embedding.

        Args:
            message: Message object to embed

        Returns:
            List of floats representing the embedding vector
        """
        snippet = message.snippet or ""
        body = (message.body or "")[:8000]  # Truncate body if too long (OpenAI has token limits)
        text = (
            f"Subject: {message.subject}\nFrom: {message.sender}\nSnippet: {snippet}\nBody: {body}"
        )
        return self._create_embedding(text)

    def embed_category(self, category: Category) -> list[float]:
        """
        Generate an embedding for a category.

        Combines name and description into a single text for embedding.

        Args:
            category: Category object to embed

        Returns:
            List of floats representing the embedding vector
        """
        # Combine name and description for embedding
        text = f"Category: {category.name}\nDescription: {category.description}"

        return self._create_embedding(text)

    def _create_embedding(self, text: str) -> list[float]:
        """
        Create an embedding for the given text using OpenAI API.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        response = self.client.embeddings.create(
            model=self.model, input=text, encoding_format="float"
        )

        return response.data[0].embedding
