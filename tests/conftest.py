"""
Pytest configuration and shared fixtures.
"""
import json
import base64
import tempfile
from pathlib import Path
from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Message
from app.stores.sqlite_store import SQLiteStore


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
        "body": base64.b64encode(b"Test email body").decode('utf-8'),
        "date": "2025-01-01T12:00:00Z"
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
            "body": base64.b64encode(b"First email body").decode('utf-8'),
            "date": "2025-01-01T12:00:00Z"
        },
        {
            "id": "msg2",
            "subject": "Test Email 2",
            "from": "Sender Two <sender2@example.com>",
            "to": ["recipient@example.com"],
            "snippet": "Second test",
            "body": base64.b64encode(b"Second email body").decode('utf-8'),
            "date": "2025-01-02T12:00:00Z"
        },
        {
            "id": "msg3",
            "subject": "Test Email 3",
            "from": "sender3@example.com",
            "to": ["recipient@example.com"],
            "snippet": "Third test",
            "body": base64.b64encode(b"Third email body").decode('utf-8'),
            "date": "2025-01-03T12:00:00Z"
        }
    ]


@pytest.fixture
def sample_jsonl_file(tmp_path, sample_messages_data):
    """Create a temporary JSONL file with sample messages."""
    file_path = tmp_path / "test_messages.jsonl"
    with open(file_path, 'w') as f:
        for msg in sample_messages_data:
            f.write(json.dumps(msg) + '\n')
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
        date=datetime(2025, 1, 1, 12, 0, 0)
    )

