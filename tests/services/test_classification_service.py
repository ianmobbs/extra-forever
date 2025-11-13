"""
Tests for app/services/classification/classification_service.py
"""

from datetime import UTC

import pytest

from app.services.categories_service import CategoriesService
from app.services.classification import ClassificationResult, ClassificationService
from app.services.classification.strategies import EmbeddingSimilarityStrategy
from app.services.messages_service import MessagesService
from models import Category, Message


class TestClassificationResult:
    """Test ClassificationResult dataclass."""

    def test_classification_result_creation(self):
        """Test creating ClassificationResult."""
        message = Message(
            id="msg1", subject="Test", sender="test@example.com", to=["recipient@example.com"]
        )
        category = Category(id=1, name="Work", description="Work emails")

        result = ClassificationResult(
            message=message,
            matched_categories=[category],
            scores=[0.85],
            explanations=["Test explanation"],
        )

        assert result.message.id == "msg1"
        assert len(result.matched_categories) == 1
        assert result.matched_categories[0].name == "Work"
        assert result.scores == [0.85]
        assert result.explanations == ["Test explanation"]


class TestClassificationService:
    """Test ClassificationService class."""

    def test_service_initialization(self, db_session):
        """Test service can be initialized with default parameters."""
        service = ClassificationService(db_session)
        assert service.db_session == db_session
        assert service.top_n == 3
        assert service.threshold == 0.5

    def test_service_initialization_with_params(self, db_session):
        """Test service can be initialized with custom parameters."""
        service = ClassificationService(db_session, top_n=5, threshold=0.7)
        assert service.top_n == 5
        assert service.threshold == 0.7

    async def test_classify_message_basic(self, db_session, mock_embedding_service):
        """Test basic message classification."""
        # Create message with embedding
        messages_service = MessagesService(db_session, mock_embedding_service)
        messages_service.create_message(
            id="msg1",
            subject="Important work deadline",
            sender="boss@company.com",
            to=["employee@company.com"],
            snippet="Please complete by Friday",
            body="We need to finish the project by Friday.",
        )

        # Create categories with embeddings
        categories_service = CategoriesService(db_session, mock_embedding_service)
        categories_service.create_category(name="Work", description="Work-related emails and tasks")
        categories_service.create_category(
            name="Personal", description="Personal emails from friends and family"
        )

        # Classify using embedding similarity strategy
        strategy = EmbeddingSimilarityStrategy()
        service = ClassificationService(db_session, strategy=strategy, top_n=2, threshold=0.0)
        result = await service.classify_message_by_id("msg1")

        assert isinstance(result, ClassificationResult)
        assert result.message.id == "msg1"
        assert len(result.matched_categories) > 0
        assert len(result.scores) == len(result.matched_categories)
        assert len(result.explanations) == len(result.matched_categories)
        # Scores should be between 0 and 1 (with small tolerance for floating point)
        for score in result.scores:
            assert score >= -0.01  # Allow small negative due to floating point
            assert score <= 1.01  # Allow slightly over 1 due to floating point
        # Explanations should be non-empty strings
        for explanation in result.explanations:
            assert isinstance(explanation, str)
            assert len(explanation) > 0

    async def test_classify_message_not_found(self, db_session):
        """Test classify with non-existent message."""
        service = ClassificationService(db_session)

        with pytest.raises(ValueError, match=r"Message with ID .* not found"):
            await service.classify_message_by_id("nonexistent")

    async def test_classify_message_no_embedding(self, sqlite_store, db_session):
        """Test classify with message that has no embedding."""
        # Create message without embedding
        message = Message(
            id="msg_no_embed",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=None,
        )
        db_session.add(message)
        db_session.commit()

        service = ClassificationService(db_session)

        with pytest.raises(ValueError, match="has no embedding"):
            await service.classify_message_by_id("msg_no_embed")

    async def test_classify_message_no_categories(self, db_session, mock_embedding_service):
        """Test classify when no categories exist."""
        # Create message with embedding
        messages_service = MessagesService(db_session, mock_embedding_service)
        messages_service.create_message(
            id="msg1", subject="Test", sender="test@example.com", to=["recipient@example.com"]
        )

        service = ClassificationService(db_session)

        with pytest.raises(ValueError, match="No categories with embeddings found"):
            await service.classify_message_by_id("msg1")

    async def test_classify_message_respects_threshold(self, db_session):
        """Test that classification respects similarity threshold."""
        # Create message with specific embedding
        message_embedding = [1.0] + [0.0] * 1535
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=message_embedding,
        )
        db_session.add(message)

        # Create category with very different embedding (low similarity)
        category_embedding = [0.0] * 1535 + [1.0]
        category = Category(
            id=1,
            name="Unrelated",
            description="Very different category",
            embedding=category_embedding,
        )
        db_session.add(category)
        db_session.commit()

        # Use high threshold - should not match
        strategy = EmbeddingSimilarityStrategy()
        service = ClassificationService(db_session, strategy=strategy, top_n=10, threshold=0.9)
        result = await service.classify_message_by_id("msg1")

        # Should have no matches above threshold
        assert len(result.matched_categories) == 0
        assert len(result.scores) == 0
        assert len(result.explanations) == 0

    async def test_classify_message_respects_top_n(self, db_session):
        """Test that classification respects top_n limit."""
        # Create message
        message_embedding = [1.0, 1.0] + [0.0] * 1534
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=message_embedding,
        )
        db_session.add(message)

        # Create 5 categories with similar embeddings
        for i in range(5):
            category_embedding = [1.0, 0.9] + [0.0] * 1534
            category = Category(
                id=i + 1,
                name=f"Category{i + 1}",
                description=f"Category {i + 1}",
                embedding=category_embedding,
            )
            db_session.add(category)
        db_session.commit()

        # Set top_n to 3
        strategy = EmbeddingSimilarityStrategy()
        service = ClassificationService(db_session, strategy=strategy, top_n=3, threshold=0.0)
        result = await service.classify_message_by_id("msg1")

        # Should only return 3 categories
        assert len(result.matched_categories) == 3
        assert len(result.scores) == 3
        assert len(result.explanations) == 3

    async def test_classify_message_scores_sorted_descending(self, db_session):
        """Test that results are sorted by score in descending order."""
        # Create message
        message_embedding = [1.0, 0.0] + [0.0] * 1534
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=message_embedding,
        )
        db_session.add(message)

        # Create categories with different similarity levels
        # High similarity
        cat1_embedding = [1.0, 0.0] + [0.0] * 1534
        cat1 = Category(id=1, name="High", description="High similarity", embedding=cat1_embedding)
        # Medium similarity
        cat2_embedding = [0.8, 0.2] + [0.0] * 1534
        cat2 = Category(
            id=2, name="Medium", description="Medium similarity", embedding=cat2_embedding
        )
        # Low similarity
        cat3_embedding = [0.5, 0.5] + [0.0] * 1534
        cat3 = Category(id=3, name="Low", description="Low similarity", embedding=cat3_embedding)
        db_session.add_all([cat1, cat2, cat3])
        db_session.commit()

        strategy = EmbeddingSimilarityStrategy()
        service = ClassificationService(db_session, strategy=strategy, top_n=10, threshold=0.0)
        result = await service.classify_message_by_id("msg1")

        # Scores should be in descending order
        for i in range(len(result.scores) - 1):
            assert result.scores[i] >= result.scores[i + 1]

    async def test_classify_and_assign(self, sqlite_store, mock_embedding_service, db_session):
        """Test classify_and_assign persists relationships."""
        # Create message
        messages_service = MessagesService(db_session, mock_embedding_service)
        messages_service.create_message(
            id="msg1", subject="Work email", sender="boss@company.com", to=["employee@company.com"]
        )

        # Create categories
        categories_service = CategoriesService(db_session, mock_embedding_service)
        categories_service.create_category(name="Work", description="Work emails")
        categories_service.create_category(name="Personal", description="Personal emails")

        # Classify and assign using embedding similarity strategy
        strategy = EmbeddingSimilarityStrategy()
        service = ClassificationService(db_session, strategy=strategy, top_n=2, threshold=0.0)
        result = await service.classify_message_by_id("msg1")

        # Verify result
        assert len(result.matched_categories) > 0

        # Extract IDs from result before accessing in new session
        result_cat_ids = {cat.id for cat in result.matched_categories}
        result_cat_count = len(result.matched_categories)

        # Verify relationships were persisted
        from app.managers.message_manager import MessageManager

        session = sqlite_store.create_session()
        try:
            manager = MessageManager(session)
            message = manager.get_by_id("msg1")
            assert len(message.categories) == result_cat_count

            # Check that category IDs match
            persisted_cat_ids = {cat.id for cat in message.categories}
            assert result_cat_ids == persisted_cat_ids
        finally:
            session.close()

    async def test_classify_and_assign_persists_metadata(
        self, sqlite_store, mock_embedding_service, db_session
    ):
        """Test that classify_and_assign persists score, explanation, and timestamp."""
        # Create message
        messages_service = MessagesService(db_session, mock_embedding_service)
        messages_service.create_message(
            id="msg1",
            subject="Important work project",
            sender="boss@company.com",
            to=["employee@company.com"],
        )

        # Create categories
        categories_service = CategoriesService(db_session, mock_embedding_service)
        categories_service.create_category(name="Work", description="Work-related emails")
        categories_service.create_category(name="Personal", description="Personal emails")

        # Classify and assign using embedding similarity strategy
        strategy = EmbeddingSimilarityStrategy()
        service = ClassificationService(db_session, strategy=strategy, top_n=2, threshold=0.0)
        result = await service.classify_message_by_id("msg1")

        # Verify result has metadata
        assert len(result.matched_categories) > 0
        assert len(result.scores) == len(result.matched_categories)
        assert len(result.explanations) == len(result.matched_categories)

        # Verify metadata was persisted
        from app.managers.message_manager import MessageManager

        session = sqlite_store.create_session()
        try:
            manager = MessageManager(session)
            message = manager.get_by_id("msg1")

            # Check that each message_category association has metadata
            assert len(message.message_categories) > 0
            for mc in message.message_categories:
                # Score should be between 0 and 1
                assert mc.score is not None
                assert 0.0 <= mc.score <= 1.0

                # Explanation should be a non-empty string
                assert mc.explanation is not None
                assert isinstance(mc.explanation, str)
                assert len(mc.explanation) > 0

                # Classified_at should be set
                assert mc.classified_at is not None

                # Category should be accessible
                assert mc.category is not None
                assert mc.category.name in ["Work", "Personal"]
        finally:
            session.close()

    async def test_classify_and_assign_clears_previous_assignments(
        self, sqlite_store, mock_embedding_service, db_session
    ):
        """Test that classify_and_assign clears previous category assignments."""
        # Create message
        messages_service = MessagesService(db_session, mock_embedding_service)
        messages_service.create_message(
            id="msg1", subject="Test", sender="test@example.com", to=["recipient@example.com"]
        )

        # Create categories
        categories_service = CategoriesService(db_session, mock_embedding_service)
        cat1 = categories_service.create_category(name="Category1", description="First category")
        categories_service.create_category(name="Category2", description="Second category")

        # Get category ID before session closes
        cat1_id = cat1.category.id

        # Manually assign category1 to message
        from datetime import datetime

        from app.managers.message_manager import MessageManager
        from models import MessageCategory

        session = sqlite_store.create_session()
        try:
            message_manager = MessageManager(session)
            message = message_manager.get_by_id("msg1")
            # Create a MessageCategory association with dummy metadata
            mc = MessageCategory(
                message_id=message.id,
                category_id=cat1_id,
                score=0.5,
                explanation="Manual assignment for testing",
                classified_at=datetime.now(UTC),
            )
            session.add(mc)
            session.commit()
        finally:
            session.close()

        # Verify initial assignment
        session = sqlite_store.create_session()
        try:
            manager = MessageManager(session)
            message = manager.get_by_id("msg1")
            assert len(message.categories) == 1
            assert message.categories[0].id == cat1_id
        finally:
            session.close()

        # Now classify and assign (should replace previous assignments)
        strategy = EmbeddingSimilarityStrategy()
        service = ClassificationService(db_session, strategy=strategy, top_n=2, threshold=0.0)
        result = await service.classify_message_by_id("msg1")

        result_cat_count = len(result.matched_categories)

        # Verify new assignments replaced old ones
        session = sqlite_store.create_session()
        try:
            manager = MessageManager(session)
            message = manager.get_by_id("msg1")
            # Should have new assignments from classification
            assert len(message.categories) == result_cat_count
        finally:
            session.close()

    def test_compute_similarity_basic(self, sqlite_store):
        """Test strategy compute_similarity with simple vectors."""
        strategy = EmbeddingSimilarityStrategy()

        # Create identical vectors (should have similarity ~1.0)
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=[1.0, 0.0, 0.0],
        )

        category = Category(
            id=1, name="Match", description="Should match", embedding=[1.0, 0.0, 0.0]
        )

        matches = strategy.classify(message, [category], top_n=10, threshold=0.5)

        assert len(matches) == 1
        assert matches[0].score == pytest.approx(1.0, abs=0.01)
        assert isinstance(matches[0].explanation, str)

    def test_compute_similarity_orthogonal_vectors(self, sqlite_store):
        """Test strategy compute_similarity with orthogonal vectors (should be ~0)."""
        strategy = EmbeddingSimilarityStrategy()

        # Orthogonal vectors (should have similarity ~0.0)
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=[1.0, 0.0, 0.0],
        )

        category = Category(
            id=1, name="Orthogonal", description="Should be orthogonal", embedding=[0.0, 1.0, 0.0]
        )

        matches = strategy.classify(message, [category], top_n=10, threshold=0.0)

        assert len(matches) == 1
        assert matches[0].score == pytest.approx(0.0, abs=0.01)

    def test_compute_similarity_opposite_vectors(self, sqlite_store):
        """Test strategy compute_similarity with opposite vectors (should be ~-1)."""
        strategy = EmbeddingSimilarityStrategy()

        # Opposite vectors (should have similarity ~-1.0)
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=[1.0, 0.0, 0.0],
        )

        category = Category(
            id=1, name="Opposite", description="Should be opposite", embedding=[-1.0, 0.0, 0.0]
        )

        matches = strategy.classify(message, [category], top_n=10, threshold=-1.0)

        assert len(matches) == 1
        assert matches[0].score == pytest.approx(-1.0, abs=0.01)

    def test_compute_similarity_multiple_categories(self, sqlite_store):
        """Test strategy compute_similarity with multiple categories."""
        strategy = EmbeddingSimilarityStrategy()

        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=[1.0, 0.0, 0.0],
        )

        categories = [
            Category(id=1, name="Cat1", description="High similarity", embedding=[1.0, 0.0, 0.0]),
            Category(id=2, name="Cat2", description="Medium similarity", embedding=[0.5, 0.5, 0.0]),
            Category(id=3, name="Cat3", description="Low similarity", embedding=[0.0, 1.0, 0.0]),
        ]

        matches = strategy.classify(message, categories, top_n=10, threshold=0.0)

        assert len(matches) == 3
        # Scores should be sorted descending
        assert matches[0].score >= matches[1].score >= matches[2].score
        # First should be highest (identical vectors)
        assert matches[0].score == pytest.approx(1.0, abs=0.01)
