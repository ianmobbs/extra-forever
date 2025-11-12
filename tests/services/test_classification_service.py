"""
Tests for app/services/classification_service.py
"""
import pytest
import numpy as np
from app.services.classification_service import (
    ClassificationService,
    ClassificationResult
)
from app.services.messages_service import MessagesService
from app.services.categories_service import CategoriesService
from models import Message, Category


class TestClassificationResult:
    """Test ClassificationResult dataclass."""
    
    def test_classification_result_creation(self):
        """Test creating ClassificationResult."""
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"]
        )
        category = Category(
            id=1,
            name="Work",
            description="Work emails"
        )
        
        result = ClassificationResult(
            message=message,
            matched_categories=[category],
            scores=[0.85]
        )
        
        assert result.message.id == "msg1"
        assert len(result.matched_categories) == 1
        assert result.matched_categories[0].name == "Work"
        assert result.scores == [0.85]


class TestClassificationService:
    """Test ClassificationService class."""
    
    def test_service_initialization(self, sqlite_store):
        """Test service can be initialized with default parameters."""
        service = ClassificationService(sqlite_store)
        assert service.store == sqlite_store
        assert service.top_n == 3
        assert service.threshold == 0.5
    
    def test_service_initialization_with_params(self, sqlite_store):
        """Test service can be initialized with custom parameters."""
        service = ClassificationService(
            sqlite_store,
            top_n=5,
            threshold=0.7
        )
        assert service.top_n == 5
        assert service.threshold == 0.7
    
    def test_classify_message_basic(
        self,
        sqlite_store,
        mock_embedding_service
    ):
        """Test basic message classification."""
        # Create message with embedding
        messages_service = MessagesService(sqlite_store, mock_embedding_service)
        message_result = messages_service.create_message(
            id="msg1",
            subject="Important work deadline",
            sender="boss@company.com",
            to=["employee@company.com"],
            snippet="Please complete by Friday",
            body="We need to finish the project by Friday."
        )
        
        # Create categories with embeddings
        categories_service = CategoriesService(sqlite_store, mock_embedding_service)
        cat1 = categories_service.create_category(
            name="Work",
            description="Work-related emails and tasks"
        )
        cat2 = categories_service.create_category(
            name="Personal",
            description="Personal emails from friends and family"
        )
        
        # Classify
        service = ClassificationService(sqlite_store, top_n=2, threshold=0.0)
        result = service.classify_message("msg1")
        
        assert isinstance(result, ClassificationResult)
        assert result.message.id == "msg1"
        assert len(result.matched_categories) > 0
        assert len(result.scores) == len(result.matched_categories)
        # Scores should be between 0 and 1 (with small tolerance for floating point)
        for score in result.scores:
            assert score >= -0.01  # Allow small negative due to floating point
            assert score <= 1.01   # Allow slightly over 1 due to floating point
    
    def test_classify_message_not_found(self, sqlite_store):
        """Test classify with non-existent message."""
        service = ClassificationService(sqlite_store)
        
        with pytest.raises(ValueError, match="Message with ID .* not found"):
            service.classify_message("nonexistent")
    
    def test_classify_message_no_embedding(
        self,
        sqlite_store,
        db_session
    ):
        """Test classify with message that has no embedding."""
        # Create message without embedding
        message = Message(
            id="msg_no_embed",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=None
        )
        db_session.add(message)
        db_session.commit()
        
        service = ClassificationService(sqlite_store)
        
        with pytest.raises(ValueError, match="has no embedding"):
            service.classify_message("msg_no_embed")
    
    def test_classify_message_no_categories(
        self,
        sqlite_store,
        mock_embedding_service
    ):
        """Test classify when no categories exist."""
        # Create message with embedding
        messages_service = MessagesService(sqlite_store, mock_embedding_service)
        messages_service.create_message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"]
        )
        
        service = ClassificationService(sqlite_store)
        
        with pytest.raises(ValueError, match="No categories with embeddings found"):
            service.classify_message("msg1")
    
    def test_classify_message_respects_threshold(
        self,
        sqlite_store,
        db_session
    ):
        """Test that classification respects similarity threshold."""
        # Create message with specific embedding
        message_embedding = [1.0] + [0.0] * 1535
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=message_embedding
        )
        db_session.add(message)
        
        # Create category with very different embedding (low similarity)
        category_embedding = [0.0] * 1535 + [1.0]
        category = Category(
            id=1,
            name="Unrelated",
            description="Very different category",
            embedding=category_embedding
        )
        db_session.add(category)
        db_session.commit()
        
        # Use high threshold - should not match
        service = ClassificationService(sqlite_store, top_n=10, threshold=0.9)
        result = service.classify_message("msg1")
        
        # Should have no matches above threshold
        assert len(result.matched_categories) == 0
        assert len(result.scores) == 0
    
    def test_classify_message_respects_top_n(
        self,
        sqlite_store,
        db_session
    ):
        """Test that classification respects top_n limit."""
        # Create message
        message_embedding = [1.0, 1.0] + [0.0] * 1534
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=message_embedding
        )
        db_session.add(message)
        
        # Create 5 categories with similar embeddings
        for i in range(5):
            category_embedding = [1.0, 0.9] + [0.0] * 1534
            category = Category(
                id=i + 1,
                name=f"Category{i+1}",
                description=f"Category {i+1}",
                embedding=category_embedding
            )
            db_session.add(category)
        db_session.commit()
        
        # Set top_n to 3
        service = ClassificationService(sqlite_store, top_n=3, threshold=0.0)
        result = service.classify_message("msg1")
        
        # Should only return 3 categories
        assert len(result.matched_categories) == 3
        assert len(result.scores) == 3
    
    def test_classify_message_scores_sorted_descending(
        self,
        sqlite_store,
        db_session
    ):
        """Test that results are sorted by score in descending order."""
        # Create message
        message_embedding = [1.0, 0.0] + [0.0] * 1534
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=message_embedding
        )
        db_session.add(message)
        
        # Create categories with different similarity levels
        # High similarity
        cat1_embedding = [1.0, 0.0] + [0.0] * 1534
        cat1 = Category(
            id=1,
            name="High",
            description="High similarity",
            embedding=cat1_embedding
        )
        # Medium similarity
        cat2_embedding = [0.8, 0.2] + [0.0] * 1534
        cat2 = Category(
            id=2,
            name="Medium",
            description="Medium similarity",
            embedding=cat2_embedding
        )
        # Low similarity
        cat3_embedding = [0.5, 0.5] + [0.0] * 1534
        cat3 = Category(
            id=3,
            name="Low",
            description="Low similarity",
            embedding=cat3_embedding
        )
        db_session.add_all([cat1, cat2, cat3])
        db_session.commit()
        
        service = ClassificationService(sqlite_store, top_n=10, threshold=0.0)
        result = service.classify_message("msg1")
        
        # Scores should be in descending order
        for i in range(len(result.scores) - 1):
            assert result.scores[i] >= result.scores[i + 1]
    
    def test_classify_and_assign(
        self,
        sqlite_store,
        mock_embedding_service,
        db_session
    ):
        """Test classify_and_assign persists relationships."""
        # Create message
        messages_service = MessagesService(sqlite_store, mock_embedding_service)
        messages_service.create_message(
            id="msg1",
            subject="Work email",
            sender="boss@company.com",
            to=["employee@company.com"]
        )
        
        # Create categories
        categories_service = CategoriesService(sqlite_store, mock_embedding_service)
        categories_service.create_category(
            name="Work",
            description="Work emails"
        )
        categories_service.create_category(
            name="Personal",
            description="Personal emails"
        )
        
        # Classify and assign
        service = ClassificationService(sqlite_store, top_n=2, threshold=0.0)
        result = service.classify_message("msg1")
        
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
    
    def test_classify_and_assign_clears_previous_assignments(
        self,
        sqlite_store,
        mock_embedding_service,
        db_session
    ):
        """Test that classify_and_assign clears previous category assignments."""
        # Create message
        messages_service = MessagesService(sqlite_store, mock_embedding_service)
        messages_service.create_message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"]
        )
        
        # Create categories
        categories_service = CategoriesService(sqlite_store, mock_embedding_service)
        cat1 = categories_service.create_category(
            name="Category1",
            description="First category"
        )
        cat2 = categories_service.create_category(
            name="Category2",
            description="Second category"
        )
        
        # Get category ID before session closes
        cat1_id = cat1.category.id
        
        # Manually assign category1 to message
        from app.managers.message_manager import MessageManager
        from app.managers.category_manager import CategoryManager
        session = sqlite_store.create_session()
        try:
            message_manager = MessageManager(session)
            category_manager = CategoryManager(session)
            message = message_manager.get_by_id("msg1")
            category = category_manager.get_by_id(cat1_id)
            message.categories = [category]
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
        service = ClassificationService(sqlite_store, top_n=2, threshold=0.0)
        result = service.classify_message("msg1")
        
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
        """Test _compute_similarity with simple vectors."""
        service = ClassificationService(sqlite_store)
        
        # Create identical vectors (should have similarity ~1.0)
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=[1.0, 0.0, 0.0]
        )
        
        category = Category(
            id=1,
            name="Match",
            description="Should match",
            embedding=[1.0, 0.0, 0.0]
        )
        
        matched_cats, scores = service._compute_similarity(message, [category])
        
        assert len(matched_cats) == 1
        assert len(scores) == 1
        assert scores[0] == pytest.approx(1.0, abs=0.01)
    
    def test_compute_similarity_orthogonal_vectors(self, sqlite_store):
        """Test _compute_similarity with orthogonal vectors (should be ~0)."""
        service = ClassificationService(sqlite_store, threshold=0.0)
        
        # Orthogonal vectors (should have similarity ~0.0)
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=[1.0, 0.0, 0.0]
        )
        
        category = Category(
            id=1,
            name="Orthogonal",
            description="Should be orthogonal",
            embedding=[0.0, 1.0, 0.0]
        )
        
        matched_cats, scores = service._compute_similarity(message, [category])
        
        assert len(matched_cats) == 1
        assert scores[0] == pytest.approx(0.0, abs=0.01)
    
    def test_compute_similarity_opposite_vectors(self, sqlite_store):
        """Test _compute_similarity with opposite vectors (should be ~-1)."""
        service = ClassificationService(sqlite_store, threshold=-1.0)
        
        # Opposite vectors (should have similarity ~-1.0)
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=[1.0, 0.0, 0.0]
        )
        
        category = Category(
            id=1,
            name="Opposite",
            description="Should be opposite",
            embedding=[-1.0, 0.0, 0.0]
        )
        
        matched_cats, scores = service._compute_similarity(message, [category])
        
        assert len(matched_cats) == 1
        assert scores[0] == pytest.approx(-1.0, abs=0.01)
    
    def test_compute_similarity_multiple_categories(self, sqlite_store):
        """Test _compute_similarity with multiple categories."""
        service = ClassificationService(sqlite_store, top_n=10, threshold=0.0)
        
        message = Message(
            id="msg1",
            subject="Test",
            sender="test@example.com",
            to=["recipient@example.com"],
            embedding=[1.0, 0.0, 0.0]
        )
        
        categories = [
            Category(
                id=1,
                name="Cat1",
                description="High similarity",
                embedding=[1.0, 0.0, 0.0]
            ),
            Category(
                id=2,
                name="Cat2",
                description="Medium similarity",
                embedding=[0.5, 0.5, 0.0]
            ),
            Category(
                id=3,
                name="Cat3",
                description="Low similarity",
                embedding=[0.0, 1.0, 0.0]
            )
        ]
        
        matched_cats, scores = service._compute_similarity(message, categories)
        
        assert len(matched_cats) == 3
        assert len(scores) == 3
        # Scores should be sorted descending
        assert scores[0] >= scores[1] >= scores[2]
        # First should be highest (identical vectors)
        assert scores[0] == pytest.approx(1.0, abs=0.01)

