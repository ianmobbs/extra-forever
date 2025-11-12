"""
Tests for LLMClassificationStrategy using pydantic-ai.
"""

import pytest
from pydantic import ValidationError
from pydantic_ai import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.services.classification.strategies import (
    CategoryMatchOutput,
    ClassificationMatch,
    LLMClassificationStrategy,
)
from models import Category, Message


class TestLLMClassificationStrategy:
    """Test LLMClassificationStrategy class."""

    def test_initialization_default_model(self):
        """Test strategy initializes with default model."""
        strategy = LLMClassificationStrategy()
        assert strategy.model == "openai:gpt-4o-mini"
        assert strategy._agent is not None

    def test_initialization_custom_model(self):
        """Test strategy initializes with custom model."""
        strategy = LLMClassificationStrategy(model="openai:gpt-4o")
        assert strategy.model == "openai:gpt-4o"
        assert strategy._agent is not None

    def test_build_message_text_full(self):
        """Test building message text with all fields."""
        strategy = LLMClassificationStrategy()
        message = Message(
            id="msg1",
            subject="Test Subject",
            sender="sender@example.com",
            to=["recipient@example.com"],
            snippet="This is a snippet",
            body="This is the full body text",
            date="2025-01-01T10:00:00Z",
        )

        text = strategy._build_message_text(message)

        assert "Subject: Test Subject" in text
        assert "From: sender@example.com" in text
        assert "To: recipient@example.com" in text
        assert "Date: 2025-01-01T10:00:00Z" in text
        assert "Preview: This is a snippet" in text
        assert "Body: This is the full body text" in text

    def test_build_message_text_minimal(self):
        """Test building message text with minimal fields."""
        strategy = LLMClassificationStrategy()
        message = Message(
            id="msg2",
            subject="Minimal",
            sender="test@example.com",
            to=["recipient@example.com"],
        )

        text = strategy._build_message_text(message)

        assert "Subject: Minimal" in text
        assert "From: test@example.com" in text
        assert "To: recipient@example.com" in text

    def test_build_message_text_multiple_recipients(self):
        """Test building message text with multiple recipients."""
        strategy = LLMClassificationStrategy()
        message = Message(
            id="msg3",
            subject="Multiple",
            sender="sender@example.com",
            to=["recipient1@example.com", "recipient2@example.com"],
        )

        text = strategy._build_message_text(message)

        assert "To: recipient1@example.com, recipient2@example.com" in text

    def test_build_message_text_truncates_long_body(self):
        """Test that very long message bodies are truncated."""
        strategy = LLMClassificationStrategy()
        long_body = "A" * 6000
        message = Message(
            id="msg4",
            subject="Long",
            sender="test@example.com",
            to=["recipient@example.com"],
            body=long_body,
        )

        text = strategy._build_message_text(message)

        assert "Body:" in text
        assert "(truncated)" in text
        assert len(text) < len(long_body)

    def test_build_multi_category_prompt(self):
        """Test building multi-category classification prompt."""
        strategy = LLMClassificationStrategy()
        categories = [
            Category(
                id=1,
                name="Work Emails",
                description="Emails related to work and professional activities",
            ),
            Category(
                id=2,
                name="Personal",
                description="Personal emails from friends and family",
            ),
        ]
        message_text = "Subject: Project Update\nFrom: boss@company.com"

        prompt = strategy._build_multi_category_prompt(message_text, categories)

        # Should contain category information with indices
        assert "[0]" in prompt
        assert "[1]" in prompt
        assert "Work Emails" in prompt
        assert "Personal" in prompt
        assert "Emails related to work and professional activities" in prompt
        assert "Personal emails from friends and family" in prompt
        # Should contain message text
        assert "Subject: Project Update" in prompt
        assert "From: boss@company.com" in prompt
        # Should instruct to use numeric indices
        assert "category_index" in prompt
        assert "0-based" in prompt.lower()

    def test_classify_no_categories(self):
        """Test classify with empty category list."""
        strategy = LLMClassificationStrategy()
        message = Message(
            id="msg1", subject="Test", sender="test@example.com", to=["recipient@example.com"]
        )

        matches = strategy.classify(message, [], top_n=3, threshold=0.5)

        assert matches == []

    def test_classify_with_match(self):
        """Test classify when LLM indicates a match."""

        # Create a mock function that returns a match
        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            # Return the structured output as text content
            import json

            response = {
                "matches": [
                    {
                        "category_index": 0,
                        "is_in_category": True,
                        "explanation": "This is a work email",
                        "confidence": 0.95,
                    }
                ]
            }
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        message = Message(
            id="msg1",
            subject="Project deadline",
            sender="boss@company.com",
            to=["employee@company.com"],
            body="We need to complete the project by Friday.",
        )

        category = Category(
            id=1,
            name="Work",
            description="Work-related emails and professional correspondence",
        )

        matches = strategy.classify(message, [category], top_n=3, threshold=0.5)

        assert len(matches) == 1
        assert matches[0].category.id == 1
        assert matches[0].category.name == "Work"
        assert matches[0].score == 0.95
        assert matches[0].explanation == "This is a work email"

    def test_classify_with_no_match(self):
        """Test classify when LLM indicates no match."""
        import json

        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            response = {
                "matches": [
                    {
                        "category_index": 0,
                        "is_in_category": False,
                        "explanation": "This is not a work email",
                        "confidence": 0.1,
                    }
                ]
            }
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        message = Message(
            id="msg1",
            subject="Dinner plans",
            sender="friend@example.com",
            to=["me@example.com"],
            body="Want to grab dinner tonight?",
        )

        category = Category(
            id=1,
            name="Work",
            description="Work-related emails",
        )

        matches = strategy.classify(message, [category], top_n=3, threshold=0.5)

        assert matches == []

    def test_classify_multiple_categories_mixed_results(self):
        """Test classify with multiple categories, some matching."""
        import json

        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            response = {
                "matches": [
                    {
                        "category_index": 0,
                        "is_in_category": True,
                        "explanation": "This is about work travel",
                        "confidence": 0.92,
                    },
                    {
                        "category_index": 1,
                        "is_in_category": False,
                        "explanation": "Not a newsletter",
                        "confidence": 0.1,
                    },
                    {
                        "category_index": 2,
                        "is_in_category": True,
                        "explanation": "This is a receipt",
                        "confidence": 0.88,
                    },
                ]
            }
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        message = Message(
            id="msg1",
            subject="Your flight receipt",
            sender="airline@example.com",
            to=["traveler@company.com"],
            body="Here is your receipt for flight ABC123.",
        )

        categories = [
            Category(id=1, name="Work Travel", description="Work-related travel receipts"),
            Category(id=2, name="Newsletters", description="Newsletter subscriptions"),
            Category(id=3, name="Receipts", description="Purchase receipts and invoices"),
        ]

        matches = strategy.classify(message, categories, top_n=10, threshold=0.5)

        assert len(matches) == 2
        # Should be sorted by confidence score descending
        assert matches[0].category.name == "Work Travel"
        assert matches[0].score == 0.92
        assert matches[1].category.name == "Receipts"
        assert matches[1].score == 0.88

    def test_classify_respects_top_n(self):
        """Test that classify respects the top_n parameter."""
        import json

        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            # Return 5 matches with different confidence scores
            response = {
                "matches": [
                    {
                        "category_index": i,
                        "is_in_category": True,
                        "explanation": f"Match {i}",
                        "confidence": 0.9 - (i * 0.1),  # Descending scores
                    }
                    for i in range(5)
                ]
            }
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
        )

        categories = [
            Category(id=i + 1, name=f"Category{i + 1}", description=f"Description {i + 1}")
            for i in range(5)
        ]

        # Request only top 2
        matches = strategy.classify(message, categories, top_n=2, threshold=0.5)

        assert len(matches) == 2
        # Should get the highest confidence matches
        assert matches[0].score == 0.9
        assert matches[1].score == 0.8

    def test_classify_respects_threshold(self):
        """Test that classify respects the threshold parameter."""
        import json

        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            response = {
                "matches": [
                    {
                        "category_index": 0,
                        "is_in_category": True,
                        "explanation": "This is a match",
                        "confidence": 0.85,
                    }
                ]
            }
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
        )

        category = Category(id=1, name="Test", description="Test category")

        # With high threshold (> 0.85), should not match
        matches = strategy.classify(message, [category], top_n=3, threshold=0.9)
        assert len(matches) == 0

        # With threshold = 0.85, should match
        matches = strategy.classify(message, [category], top_n=3, threshold=0.85)
        assert len(matches) == 1

        # With low threshold, should match
        matches = strategy.classify(message, [category], top_n=3, threshold=0.0)
        assert len(matches) == 1

    def test_classify_returns_classification_match(self):
        """Test that classify returns proper ClassificationMatch objects."""
        import json

        def mock_model_func(messages, info: AgentInfo) -> ModelResponse:
            response = {
                "matches": [
                    {
                        "category_index": 0,
                        "is_in_category": True,
                        "explanation": "Email contains work-related keywords and sender domain",
                        "confidence": 0.93,
                    }
                ]
            }
            return ModelResponse(parts=[TextPart(content=json.dumps(response))])

        function_model = FunctionModel(mock_model_func)

        strategy = LLMClassificationStrategy()
        strategy._agent._model = function_model

        message = Message(
            id="msg1",
            subject="Q4 Report",
            sender="manager@company.com",
            to=["team@company.com"],
        )

        category = Category(id=1, name="Work", description="Work emails")

        matches = strategy.classify(message, [category], top_n=3, threshold=0.5)

        assert len(matches) == 1
        match = matches[0]
        assert isinstance(match, ClassificationMatch)
        assert isinstance(match.category, Category)
        assert isinstance(match.score, float)
        assert isinstance(match.explanation, str)
        assert match.category == category
        assert match.score == 0.93
        assert "work-related keywords" in match.explanation.lower()


class TestCategoryMatchOutput:
    """Test CategoryMatchOutput Pydantic model."""

    def test_valid_output(self):
        """Test creating valid CategoryMatchOutput."""
        output = CategoryMatchOutput(
            category_index=0,
            is_in_category=True,
            explanation="This email is about work-related travel",
            confidence=0.87,
        )

        assert output.category_index == 0
        assert output.is_in_category is True
        assert output.explanation == "This email is about work-related travel"
        assert output.confidence == 0.87

    def test_output_false_match(self):
        """Test creating output for non-match."""
        output = CategoryMatchOutput(
            category_index=1,
            is_in_category=False,
            explanation="This email is not related to the category",
            confidence=0.15,
        )

        assert output.category_index == 1
        assert output.is_in_category is False
        assert output.explanation == "This email is not related to the category"
        assert output.confidence == 0.15

    def test_output_validation(self):
        """Test that output validates required fields."""
        with pytest.raises(ValidationError):  # Pydantic will raise validation error
            CategoryMatchOutput(  # type: ignore
                is_in_category=True, explanation="Test", confidence=0.9
            )  # Missing category_index

        with pytest.raises(ValidationError):
            CategoryMatchOutput(  # type: ignore
                category_index=0, explanation="Test", confidence=0.9
            )  # Missing is_in_category
