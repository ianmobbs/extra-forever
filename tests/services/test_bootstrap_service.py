"""
Tests for app/services/bootstrap_service.py
"""

import base64
import json
from pathlib import Path

from pydantic_ai import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.services.bootstrap_service import BootstrapResult, BootstrapService
from app.services.categories_service import CategoriesService
from app.services.messages_service import ClassificationOptions, MessagesService


class TestBootstrapService:
    """Test BootstrapService class."""

    def test_service_initialization(self, db_session, sqlite_store, mock_embedding_service):
        """Test service can be initialized."""
        messages_service = MessagesService(db_session, mock_embedding_service, store=sqlite_store)
        categories_service = CategoriesService(db_session, mock_embedding_service)
        service = BootstrapService(sqlite_store, messages_service, categories_service)
        assert service.store == sqlite_store

    def test_bootstrap_with_messages_only(
        self, db_session, sqlite_store, sample_jsonl_file, mock_embedding_service
    ):
        """Test bootstrapping with messages only."""
        messages_service = MessagesService(db_session, mock_embedding_service, store=sqlite_store)
        categories_service = CategoriesService(db_session, mock_embedding_service)
        service = BootstrapService(sqlite_store, messages_service, categories_service)

        result = service.bootstrap(
            messages_file=sample_jsonl_file, categories_file=None, drop_existing=True
        )

        assert isinstance(result, BootstrapResult)
        assert result.total_messages == 3
        assert result.total_categories == 0
        assert result.total_classified == 0
        assert len(result.preview_messages) == 3
        assert len(result.preview_categories) == 0

    def test_bootstrap_with_categories_only(
        self, db_session, sqlite_store, tmp_path, mock_embedding_service
    ):
        """Test bootstrapping with categories only."""
        # Create sample categories file
        categories_file = tmp_path / "categories.jsonl"
        with open(categories_file, "w") as f:
            f.write('{"name": "Work", "description": "Work emails"}\n')
            f.write('{"name": "Personal", "description": "Personal emails"}\n')

        messages_service = MessagesService(db_session, mock_embedding_service, store=sqlite_store)
        categories_service = CategoriesService(db_session, mock_embedding_service)
        service = BootstrapService(sqlite_store, messages_service, categories_service)

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
        self, db_session, sqlite_store, sample_jsonl_file, tmp_path, mock_embedding_service
    ):
        """Test bootstrapping with both messages and categories."""
        # Create sample categories file
        categories_file = tmp_path / "categories.jsonl"
        with open(categories_file, "w") as f:
            f.write('{"name": "Work", "description": "Work emails"}\n')
            f.write('{"name": "Personal", "description": "Personal emails"}\n')

        messages_service = MessagesService(db_session, mock_embedding_service, store=sqlite_store)
        categories_service = CategoriesService(db_session, mock_embedding_service)
        service = BootstrapService(sqlite_store, messages_service, categories_service)

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
        self,
        db_session,
        sqlite_store,
        sample_jsonl_file,
        tmp_path,
        mock_embedding_service,
        monkeypatch,
    ):
        """Test bootstrapping with auto-classification."""
        # Create sample categories file
        categories_file = tmp_path / "categories.jsonl"
        with open(categories_file, "w") as f:
            f.write('{"name": "Work", "description": "Work emails"}\n')
            f.write('{"name": "Personal", "description": "Personal emails"}\n')

        # Create a mock function that always returns True for classification
        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            return ModelResponse(
                parts=[
                    TextPart(
                        content=json.dumps(
                            {
                                "is_in_category": True,
                                "explanation": "This message matches the category",
                            }
                        )
                    )
                ]
            )

        function_model = FunctionModel(mock_model_func)

        # Patch LLMClassificationStrategy to use our mock model
        from app.services.classification.strategies import LLMClassificationStrategy

        original_init = LLMClassificationStrategy.__init__

        def patched_init(self, model: str = "openai:gpt-4o-mini"):
            original_init(self, model)
            self._agent._model = function_model

        monkeypatch.setattr(LLMClassificationStrategy, "__init__", patched_init)

        messages_service = MessagesService(db_session, mock_embedding_service, store=sqlite_store)
        categories_service = CategoriesService(db_session, mock_embedding_service)
        service = BootstrapService(sqlite_store, messages_service, categories_service)

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

    def test_bootstrap_skips_empty_lines(
        self, db_session, sqlite_store, tmp_path, mock_embedding_service
    ):
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

        messages_service = MessagesService(db_session, mock_embedding_service, store=sqlite_store)
        categories_service = CategoriesService(db_session, mock_embedding_service)
        service = BootstrapService(sqlite_store, messages_service, categories_service)

        result = service.bootstrap(
            messages_file=messages_file, categories_file=categories_file, drop_existing=True
        )

        assert result.total_messages == 1
        assert result.total_categories == 1

    def test_bootstrap_with_nonexistent_files(
        self, db_session, sqlite_store, mock_embedding_service
    ):
        """Test bootstrapping with nonexistent files doesn't crash."""
        messages_service = MessagesService(db_session, mock_embedding_service, store=sqlite_store)
        categories_service = CategoriesService(db_session, mock_embedding_service)
        service = BootstrapService(sqlite_store, messages_service, categories_service)

        result = service.bootstrap(
            messages_file=Path("/nonexistent/messages.jsonl"),
            categories_file=Path("/nonexistent/categories.jsonl"),
            drop_existing=True,
        )

        assert result.total_messages == 0
        assert result.total_categories == 0
        assert result.total_classified == 0
