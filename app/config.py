"""
Application configuration.

Centralizes all configuration values with sensible defaults.
Override via environment variables when needed.
"""

import os
from pathlib import Path


class Config:
    """Application configuration."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///messages.db")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"

    # Classification defaults
    CLASSIFICATION_TOP_N: int = int(os.getenv("CLASSIFICATION_TOP_N", "3"))
    CLASSIFICATION_THRESHOLD: float = float(os.getenv("CLASSIFICATION_THRESHOLD", "0.5"))

    # OpenAI / Embedding
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))

    # Paths for sample data
    SAMPLE_MESSAGES_PATH: Path = Path(os.getenv("SAMPLE_MESSAGES_PATH", "sample-messages.jsonl"))
    SAMPLE_CATEGORIES_PATH: Path = Path(
        os.getenv("SAMPLE_CATEGORIES_PATH", "sample-categories.jsonl")
    )


# Global config instance
config = Config()
