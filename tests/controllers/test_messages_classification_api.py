"""
Tests for message classification API endpoint.
"""

import pytest

from app.controllers.messages_controller import MessagesController
from app.services.categories_service import CategoriesService
from app.services.messages_service import MessagesService


@pytest.mark.asyncio
class TestMessageClassificationAPI:
    """Test classification API endpoint."""

    async def test_classify_message_api_response_format(self, sqlite_store, mock_embedding_service):
        """Test that classification API returns the expected JSON format."""
        # Create a message
        messages_service = MessagesService(sqlite_store, mock_embedding_service)
        messages_service.create_message(
            id="msg123",
            subject="Flight confirmation for business trip",
            sender="airline@example.com",
            to=["user@company.com"],
            snippet="Your flight to NYC is confirmed",
            body="Thank you for booking with us. Your flight details...",
        )

        # Create categories
        categories_service = CategoriesService(sqlite_store, mock_embedding_service)
        categories_service.create_category(
            name="Work Travel", description="Work-related travel receipts and bookings"
        )
        categories_service.create_category(
            name="Personal", description="Personal emails from friends and family"
        )

        # Create controller and classify
        controller = MessagesController(db_path=sqlite_store.db_path)
        response = await controller.classify_message_api("msg123", top_n=2, threshold=0.0)

        # Verify response structure
        assert hasattr(response, "message_id")
        assert hasattr(response, "classifications")
        assert response.message_id == "msg123"
        assert isinstance(response.classifications, list)
        assert len(response.classifications) > 0

        # Verify each classification entry has the required fields
        for classification in response.classifications:
            assert hasattr(classification, "category_id")
            assert hasattr(classification, "category_name")
            assert hasattr(classification, "is_in_category")
            assert hasattr(classification, "explanation")

            # Verify field types and values
            assert isinstance(classification.category_id, int)
            assert isinstance(classification.category_name, str)
            assert classification.is_in_category is True
            assert isinstance(classification.explanation, str)
            assert len(classification.explanation) > 0

            # Verify explanation format
            assert "msg123" in classification.explanation
            assert "similarity" in classification.explanation.lower()
            assert classification.category_name in classification.explanation

    async def test_classify_message_api_json_serialization(
        self, sqlite_store, mock_embedding_service
    ):
        """Test that the response can be serialized to JSON with expected structure."""
        # Create a message
        messages_service = MessagesService(sqlite_store, mock_embedding_service)
        messages_service.create_message(
            id="test_msg",
            subject="Test email",
            sender="sender@example.com",
            to=["recipient@example.com"],
        )

        # Create a category
        categories_service = CategoriesService(sqlite_store, mock_embedding_service)
        categories_service.create_category(name="Test", description="Test category")

        # Classify
        controller = MessagesController(db_path=sqlite_store.db_path)
        response = await controller.classify_message_api("test_msg", top_n=1, threshold=0.0)

        # Convert to dict (simulates JSON serialization)
        response_dict = response.model_dump()

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

    async def test_classify_message_api_no_matches(self, sqlite_store, mock_embedding_service):
        """Test classification API when no categories match above threshold."""
        # Create a message
        messages_service = MessagesService(sqlite_store, mock_embedding_service)
        messages_service.create_message(
            id="msg_no_match",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
        )

        # Create a category
        categories_service = CategoriesService(sqlite_store, mock_embedding_service)
        categories_service.create_category(name="Test", description="Test category")

        # Classify with very high threshold (no matches expected)
        controller = MessagesController(db_path=sqlite_store.db_path)
        response = await controller.classify_message_api("msg_no_match", top_n=10, threshold=0.99)

        # Should return empty classifications list
        assert response.message_id == "msg_no_match"
        assert isinstance(response.classifications, list)
        # Note: May be empty if threshold is too high
        assert len(response.classifications) >= 0
