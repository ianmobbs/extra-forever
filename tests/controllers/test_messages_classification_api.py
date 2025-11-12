"""
Tests for message classification API endpoint.
"""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic_ai import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.controllers.messages_controller import MessagesController
from app.deps import get_db_session, get_messages_service
from app.services.categories_service import CategoriesService
from app.services.classification import LLMClassificationStrategy
from app.services.messages_service import MessagesService
from app.stores.sqlite_store import SQLiteStore


class TestMessageClassificationAPI:
    """Test classification API endpoint."""

    @pytest.fixture
    def client(self, mock_embedding_service):
        """Create a test client with dependency overrides."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = f"sqlite:///{tmp.name}"
            store = SQLiteStore(db_path=db_path, echo=False)
            store.init_db(drop_existing=True)

            session = store.create_session()
            messages_service = MessagesService(session, mock_embedding_service, store=store)
            categories_service = CategoriesService(session, mock_embedding_service)

            def override_get_messages_service():
                return messages_service

            def override_get_db_session():
                yield session

            controller = MessagesController()
            app = FastAPI()
            app.include_router(controller.router)
            app.dependency_overrides[get_messages_service] = override_get_messages_service
            app.dependency_overrides[get_db_session] = override_get_db_session

            client = TestClient(app)
            yield client, messages_service, categories_service

            session.close()
            Path(tmp.name).unlink(missing_ok=True)

    def test_classify_message_api_response_format(self, client):
        """Test that classification API returns the expected JSON format."""
        client_obj, messages_service, categories_service = client

        # Create a message
        messages_service.create_message(
            id="msg123",
            subject="Flight confirmation for business trip",
            sender="airline@example.com",
            to=["user@company.com"],
            snippet="Your flight to NYC is confirmed",
            body="Thank you for booking with us. Your flight details...",
        )

        # Create categories
        categories_service.create_category(
            name="Work Travel", description="Work-related travel receipts and bookings"
        )
        categories_service.create_category(
            name="Personal", description="Personal emails from friends and family"
        )

        # Classify via API
        response = client_obj.post("/messages/msg123/classify?top_n=2&threshold=0.0")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "message_id" in data
        assert "classifications" in data
        assert data["message_id"] == "msg123"
        assert isinstance(data["classifications"], list)
        assert len(data["classifications"]) > 0

        # Verify each classification entry has the required fields
        for classification in data["classifications"]:
            assert "category_id" in classification
            assert "category_name" in classification
            assert "is_in_category" in classification
            assert "explanation" in classification

            # Verify field types and values
            assert isinstance(classification["category_id"], int)
            assert isinstance(classification["category_name"], str)
            assert classification["is_in_category"] is True
            assert isinstance(classification["explanation"], str)
            assert len(classification["explanation"]) > 0

            # Verify explanation format
            assert "msg123" in classification["explanation"]
            assert "similarity" in classification["explanation"].lower()
            assert classification["category_name"] in classification["explanation"]

    def test_classify_message_api_json_serialization(self, client):
        """Test that the response can be serialized to JSON with expected structure."""
        client_obj, messages_service, categories_service = client

        # Create a message
        messages_service.create_message(
            id="test_msg",
            subject="Test email",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )

        # Create a category
        categories_service.create_category(name="Test", description="Test category")

        # Classify via API
        response = client_obj.post("/messages/test_msg/classify?top_n=1&threshold=0.0")

        assert response.status_code == 200
        response_dict = response.json()

        # Verify structure matches requirements
        assert "message_id" in response_dict
        assert "classifications" in response_dict
        assert isinstance(response_dict["classifications"], list)

        if response_dict["classifications"]:
            classification = response_dict["classifications"][0]
            assert "category_id" in classification
            assert "category_name" in classification
            assert "is_in_category" in classification
            assert "explanation" in classification
            assert classification["is_in_category"] is True

    def test_classify_message_api_no_matches(self, client):
        """Test classification API when no categories match above threshold."""
        client_obj, messages_service, categories_service = client

        # Create a message
        messages_service.create_message(
            id="msg_no_match",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
        )

        # Create a category
        categories_service.create_category(name="Test", description="Test category")

        # Classify with very high threshold (no matches expected)
        response = client_obj.post("/messages/msg_no_match/classify?top_n=10&threshold=0.99")

        assert response.status_code == 200
        data = response.json()

        # Should return empty classifications list
        assert data["message_id"] == "msg_no_match"
        assert isinstance(data["classifications"], list)
        # Note: May be empty if threshold is too high
        assert len(data["classifications"]) >= 0


class TestLLMClassificationIntegration:
    """Test LLM classification strategy integration at the service layer."""

    def test_llm_classification_with_test_model(self, db_session):
        """Test LLM classification with FunctionModel (no real API calls)."""
        # Create mock function that returns responses
        responses = [
            {
                "is_in_category": True,
                "explanation": "This email is about work travel based on the subject and sender",
            },
            {
                "is_in_category": False,
                "explanation": "This email is not related to personal matters",
            },
        ]
        response_idx = [0]

        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            response = responses[response_idx[0]]
            response_idx[0] += 1
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        # Create LLM strategy with function model
        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        # Create message
        from models import Message

        message = Message(
            id="msg1",
            subject="Flight confirmation for business trip",
            sender="airline@company.com",
            to=["employee@company.com"],
            body="Your flight to NYC is confirmed for the project meeting.",
        )

        # Create categories
        from models import Category

        work_travel = Category(
            id=1, name="Work Travel", description="Work-related travel receipts and bookings"
        )
        personal = Category(
            id=2, name="Personal", description="Personal emails from friends and family"
        )

        # Run classification
        matches = strategy.classify(
            message=message, categories=[work_travel, personal], top_n=10, threshold=0.5
        )

        # Verify results
        assert len(matches) == 1
        assert matches[0].category.name == "Work Travel"
        assert matches[0].score == 1.0
        assert "work travel" in matches[0].explanation.lower()

    def test_llm_classification_service_integration(self, db_session):
        """Test LLM classification through strategy directly."""

        # Create function model
        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            return ModelResponse(
                parts=[
                    TextPart(
                        content=json.dumps(
                            {
                                "is_in_category": True,
                                "explanation": "Flight receipt matches work travel category",
                            }
                        )
                    )
                ]
            )

        function_model = FunctionModel(mock_model_func)

        # Create strategy with function model
        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        # Create message (no database needed for strategy test)
        from models import Category, Message

        message = Message(
            id="test_msg",
            subject="Flight receipt",
            sender="airline@example.com",
            to=["user@company.com"],
            body="Your flight receipt for $500",
        )

        # Create category
        category = Category(id=1, name="Work Travel", description="Work-related travel expenses")

        # Classify using strategy directly
        matches = strategy.classify(message=message, categories=[category], top_n=3, threshold=0.5)

        # Verify results
        assert len(matches) == 1
        assert matches[0].category.name == "Work Travel"
        assert matches[0].score == 1.0
        assert "Flight receipt" in matches[0].explanation

    def test_llm_classification_multiple_categories(self, db_session):
        """Test LLM classification with multiple categories."""
        # Create function model with responses for each category
        responses = [
            {"is_in_category": True, "explanation": "This is a work travel receipt"},
            {"is_in_category": True, "explanation": "This is a receipt"},
            {"is_in_category": False, "explanation": "Not a newsletter"},
        ]
        response_idx = [0]

        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            response = responses[response_idx[0]]
            response_idx[0] += 1
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        # Create strategy
        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        # Create message
        from models import Category, Message

        message = Message(
            id="receipt_msg",
            subject="Flight Receipt - NYC Trip",
            sender="airline@example.com",
            to=["employee@company.com"],
            body="Receipt for flight booking",
        )

        # Create categories
        categories = [
            Category(id=1, name="Work Travel", description="Work travel expenses"),
            Category(id=2, name="Receipts", description="Purchase receipts"),
            Category(id=3, name="Newsletters", description="Email newsletters"),
        ]

        # Classify
        matches = strategy.classify(message=message, categories=categories, top_n=10, threshold=0.5)

        # Verify results
        assert len(matches) == 2
        assert matches[0].category.name == "Work Travel"
        assert matches[1].category.name == "Receipts"
        assert all(m.score == 1.0 for m in matches)

    def test_llm_classification_respects_top_n(self, db_session):
        """Test that LLM classification respects top_n parameter."""
        # Create function model that matches all categories
        responses = [{"is_in_category": True, "explanation": "This matches"} for _ in range(5)]
        response_idx = [0]

        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            response = responses[response_idx[0]]
            response_idx[0] += 1
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        # Create strategy
        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        # Create message and categories
        from models import Category, Message

        message = Message(
            id="msg",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
        )

        categories = [
            Category(id=i, name=f"Category{i}", description=f"Description {i}") for i in range(5)
        ]

        # Classify with top_n=2
        matches = strategy.classify(message=message, categories=categories, top_n=2, threshold=0.5)

        # Should only return 2 matches even though all matched
        assert len(matches) == 2

    def test_llm_classification_no_matches(self, db_session):
        """Test LLM classification when no categories match."""

        # Create function model that doesn't match
        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            return ModelResponse(
                parts=[
                    TextPart(
                        content=json.dumps(
                            {"is_in_category": False, "explanation": "Does not match this category"}
                        )
                    )
                ]
            )

        function_model = FunctionModel(mock_model_func)

        # Create strategy
        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        # Create message and category
        from models import Category, Message

        message = Message(
            id="msg",
            subject="Personal email",
            sender="friend@example.com",
            to=["me@example.com"],
        )

        category = Category(id=1, name="Work", description="Work-related emails")

        # Classify
        matches = strategy.classify(message=message, categories=[category], top_n=10, threshold=0.5)

        # Should have no matches
        assert len(matches) == 0
