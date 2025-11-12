"""
Pytest configuration and shared fixtures.
"""

import base64
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from app.services.embedding_service import EmbeddingService
from app.stores.sqlite_store import SQLiteStore
from models import Category, Message


@pytest.fixture
def temp_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = f"sqlite:///{tmp.name}"
        yield db_path
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def sqlite_store(temp_db):
    """Create a SQLiteStore instance with a temporary database."""
    store = SQLiteStore(db_path=temp_db, echo=False)
    store.init_db(drop_existing=True)
    yield store


@pytest.fixture
def db_session(sqlite_store):
    """Create a database session for testing."""
    session = sqlite_store.create_session()
    yield session
    session.close()


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "id": "test123",
        "subject": "Test Email",
        "from": "Sender <sender@example.com>",
        "to": ["recipient@example.com"],
        "snippet": "This is a test",
        "body": base64.b64encode(b"Test email body").decode("utf-8"),
        "date": "2025-01-01T12:00:00Z",
    }


@pytest.fixture
def sample_messages_data():
    """Multiple sample messages for testing."""
    return [
        {
            "id": "msg1",
            "subject": "Test Email 1",
            "from": "Sender One <sender1@example.com>",
            "to": ["recipient@example.com"],
            "snippet": "First test",
            "body": base64.b64encode(b"First email body").decode("utf-8"),
            "date": "2025-01-01T12:00:00Z",
        },
        {
            "id": "msg2",
            "subject": "Test Email 2",
            "from": "Sender Two <sender2@example.com>",
            "to": ["recipient@example.com"],
            "snippet": "Second test",
            "body": base64.b64encode(b"Second email body").decode("utf-8"),
            "date": "2025-01-02T12:00:00Z",
        },
        {
            "id": "msg3",
            "subject": "Test Email 3",
            "from": "sender3@example.com",
            "to": ["recipient@example.com"],
            "snippet": "Third test",
            "body": base64.b64encode(b"Third email body").decode("utf-8"),
            "date": "2025-01-03T12:00:00Z",
        },
    ]


@pytest.fixture
def sample_jsonl_file(tmp_path, sample_messages_data):
    """Create a temporary JSONL file with sample messages."""
    file_path = tmp_path / "test_messages.jsonl"
    with open(file_path, "w") as f:
        for msg in sample_messages_data:
            f.write(json.dumps(msg) + "\n")
    return file_path


@pytest.fixture
def sample_message():
    """Create a sample Message ORM object."""
    return Message(
        id="test123",
        subject="Test Subject",
        sender="Test Sender <test@example.com>",
        to=["recipient@example.com"],
        snippet="Test snippet",
        body="Test body content",
        date=datetime(2025, 1, 1, 12, 0, 0),
    )


class MockEmbeddingService(EmbeddingService):
    """Mock embedding service for testing that doesn't make API calls."""

    def __init__(self):
        # Don't call parent __init__ to avoid creating OpenAI client
        import random

        self.rng = random.Random(42)  # Use a fixed seed for reproducibility

    def embed_message(self, message: Message) -> list[float]:
        """Return a deterministic random embedding vector based on message content."""
        # Generate deterministic embeddings based on message ID
        seed = hash(message.id) % (2**32) if message.id else 42
        rng = self.rng.__class__(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(1536)]

    def embed_category(self, category: Category) -> list[float]:
        """Return a deterministic random embedding vector based on category name."""
        # Generate deterministic embeddings based on category name
        seed = hash(category.name) % (2**32) if category.name else 43
        rng = self.rng.__class__(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(1536)]


@pytest.fixture
def mock_embedding_service():
    """Provide a mock embedding service for testing."""
    return MockEmbeddingService()


@pytest.fixture(autouse=True)
def patch_embedding_service(monkeypatch):
    """
    Automatically patch EmbeddingService with MockEmbeddingService for all tests.
    This ensures tests don't require an OpenAI API key.
    """
    # Patch the EmbeddingService class in all modules where it's imported
    monkeypatch.setattr("app.services.embedding_service.EmbeddingService", MockEmbeddingService)
    monkeypatch.setattr("app.services.categories_service.EmbeddingService", MockEmbeddingService)
    monkeypatch.setattr("app.services.messages_service.EmbeddingService", MockEmbeddingService)
