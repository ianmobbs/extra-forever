"""
Tests for app/services/bootstrap_service.py
"""

import base64
import json
from pathlib import Path

from app.services.bootstrap_service import BootstrapResult, BootstrapService
from app.services.messages_service import ClassificationOptions


class TestBootstrapService:
    """Test BootstrapService class."""

    def test_service_initialization(self, sqlite_store):
        """Test service can be initialized."""
        service = BootstrapService(sqlite_store)
        assert service.store == sqlite_store

    def test_bootstrap_with_messages_only(
        self, sqlite_store, sample_jsonl_file, mock_embedding_service
    ):
        """Test bootstrapping with messages only."""
        service = BootstrapService(sqlite_store)
        # Inject mock embedding service
        service.messages_service.embedding_service = mock_embedding_service

        result = service.bootstrap(
            messages_file=sample_jsonl_file, categories_file=None, drop_existing=True
        )

        assert isinstance(result, BootstrapResult)
        assert result.total_messages == 3
        assert result.total_categories == 0
        assert result.total_classified == 0
        assert len(result.preview_messages) == 3
        assert len(result.preview_categories) == 0

    def test_bootstrap_with_categories_only(self, sqlite_store, tmp_path, mock_embedding_service):
        """Test bootstrapping with categories only."""
        # Create sample categories file
        categories_file = tmp_path / "categories.jsonl"
        with open(categories_file, "w") as f:
            f.write('{"name": "Work", "description": "Work emails"}\n')
            f.write('{"name": "Personal", "description": "Personal emails"}\n')

        service = BootstrapService(sqlite_store)
        # Inject mock embedding service
        service.categories_service.embedding_service = mock_embedding_service

        result = service.bootstrap(
            messages_file=None, categories_file=categories_file, drop_existing=True
        )

        assert isinstance(result, BootstrapResult)
        assert result.total_messages == 0
        assert result.total_categories == 2
        assert result.total_classified == 0
        assert len(result.preview_messages) == 0
        assert len(result.preview_categories) == 2

    def test_bootstrap_with_messages_and_categories(
        self, sqlite_store, sample_jsonl_file, tmp_path, mock_embedding_service
    ):
        """Test bootstrapping with both messages and categories."""
        # Create sample categories file
        categories_file = tmp_path / "categories.jsonl"
        with open(categories_file, "w") as f:
            f.write('{"name": "Work", "description": "Work emails"}\n')
            f.write('{"name": "Personal", "description": "Personal emails"}\n')

        service = BootstrapService(sqlite_store)
        # Inject mock embedding service
        service.messages_service.embedding_service = mock_embedding_service
        service.categories_service.embedding_service = mock_embedding_service

        result = service.bootstrap(
            messages_file=sample_jsonl_file, categories_file=categories_file, drop_existing=True
        )

        assert isinstance(result, BootstrapResult)
        assert result.total_messages == 3
        assert result.total_categories == 2
        assert result.total_classified == 0  # Not auto-classified
        assert len(result.preview_messages) == 3
        assert len(result.preview_categories) == 2

    def test_bootstrap_with_auto_classify(
        self, sqlite_store, sample_jsonl_file, tmp_path, mock_embedding_service
    ):
        """Test bootstrapping with auto-classification."""
        # Create sample categories file
        categories_file = tmp_path / "categories.jsonl"
        with open(categories_file, "w") as f:
            f.write('{"name": "Work", "description": "Work emails"}\n')
            f.write('{"name": "Personal", "description": "Personal emails"}\n')

        service = BootstrapService(sqlite_store)
        # Inject mock embedding service
        service.messages_service.embedding_service = mock_embedding_service
        service.categories_service.embedding_service = mock_embedding_service

        classification_opts = ClassificationOptions(auto_classify=True, top_n=2, threshold=0.0)

        result = service.bootstrap(
            messages_file=sample_jsonl_file,
            categories_file=categories_file,
            drop_existing=True,
            classification_options=classification_opts,
        )

        assert isinstance(result, BootstrapResult)
        assert result.total_messages == 3
        assert result.total_categories == 2
        assert result.total_classified == 3  # All messages classified
        assert len(result.preview_messages) == 3
        assert len(result.preview_categories) == 2

        # Verify messages have categories assigned
        session = sqlite_store.create_session()
        try:
            from app.managers.message_manager import MessageManager

            manager = MessageManager(session)
            messages = manager.get_all()
            for msg in messages:
                assert len(msg.categories) > 0
        finally:
            session.close()

    def test_bootstrap_skips_empty_lines(self, sqlite_store, tmp_path, mock_embedding_service):
        """Test that bootstrap skips empty lines in files."""
        # Create sample files with empty lines
        messages_file = tmp_path / "messages.jsonl"
        with open(messages_file, "w") as f:
            msg = {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "to": ["recipient@example.com"],
                "snippet": "snippet",
                "body": base64.b64encode(b"body").decode("utf-8"),
                "date": "2025-01-01T12:00:00Z",
            }
            f.write(json.dumps(msg) + "\n")
            f.write("\n")  # Empty line
            f.write("\n")  # Another empty line

        categories_file = tmp_path / "categories.jsonl"
        with open(categories_file, "w") as f:
            f.write('{"name": "Work", "description": "Work emails"}\n')
            f.write("\n")  # Empty line

        service = BootstrapService(sqlite_store)
        # Inject mock embedding service
        service.messages_service.embedding_service = mock_embedding_service
        service.categories_service.embedding_service = mock_embedding_service

        result = service.bootstrap(
            messages_file=messages_file, categories_file=categories_file, drop_existing=True
        )

        assert result.total_messages == 1
        assert result.total_categories == 1

    def test_bootstrap_with_nonexistent_files(self, sqlite_store):
        """Test bootstrapping with nonexistent files doesn't crash."""
        service = BootstrapService(sqlite_store)

        result = service.bootstrap(
            messages_file=Path("/nonexistent/messages.jsonl"),
            categories_file=Path("/nonexistent/categories.jsonl"),
            drop_existing=True,
        )

        assert result.total_messages == 0
        assert result.total_categories == 0
        assert result.total_classified == 0
