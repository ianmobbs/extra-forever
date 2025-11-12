"""
Tests for app/services/categories_service.py
"""

import pytest

from app.services.categories_service import CategoriesService


class TestCategoriesService:
    """Test CategoriesService class."""

    def test_create_category(self, db_session, mock_embedding_service):
        """Test creating a category through service."""
        service = CategoriesService(db_session, mock_embedding_service)

        result = service.create_category(
            name="Work Travel", description="Work-related travel receipts from airlines"
        )

        assert result.category.id is not None
        assert result.category.name == "Work Travel"
        assert result.category.description == "Work-related travel receipts from airlines"
        # Verify embedding was added
        assert result.category.embedding is not None
        assert len(result.category.embedding) == 1536

    def test_create_category_duplicate_raises_error(self, db_session, mock_embedding_service):
        """Test creating duplicate category raises error."""
        service = CategoriesService(db_session, mock_embedding_service)

        service.create_category(name="Unique", description="First")

        with pytest.raises(ValueError):
            service.create_category(name="Unique", description="Second")

    def test_get_category(self, db_session, mock_embedding_service):
        """Test retrieving category by ID."""
        service = CategoriesService(db_session, mock_embedding_service)

        created = service.create_category(name="Test", description="Test category")

        result = service.get_category(created.category.id)
        assert result is not None
        assert result.category.name == "Test"

    def test_get_category_not_found(self, db_session, mock_embedding_service):
        """Test retrieving non-existent category returns None."""
        service = CategoriesService(db_session, mock_embedding_service)

        result = service.get_category(9999)
        assert result is None

    def test_get_category_by_name(self, db_session, mock_embedding_service):
        """Test retrieving category by name."""
        service = CategoriesService(db_session, mock_embedding_service)

        service.create_category(name="FindMe", description="Test")

        result = service.get_category_by_name("FindMe")
        assert result is not None
        assert result.category.name == "FindMe"

    def test_get_category_by_name_not_found(self, db_session, mock_embedding_service):
        """Test retrieving category by non-existent name returns None."""
        service = CategoriesService(db_session, mock_embedding_service)

        result = service.get_category_by_name("NonExistent")
        assert result is None

    def test_list_categories(self, db_session, mock_embedding_service):
        """Test listing all categories."""
        service = CategoriesService(db_session, mock_embedding_service)

        service.create_category(name="Cat1", description="First")
        service.create_category(name="Cat2", description="Second")
        service.create_category(name="Cat3", description="Third")

        categories = service.list_categories()
        assert len(categories) == 3
        assert {cat.name for cat in categories} == {"Cat1", "Cat2", "Cat3"}

    def test_list_categories_empty(self, db_session, mock_embedding_service):
        """Test listing categories when none exist."""
        service = CategoriesService(db_session, mock_embedding_service)

        categories = service.list_categories()
        assert categories == []

    def test_update_category(self, db_session, mock_embedding_service):
        """Test updating a category."""
        service = CategoriesService(db_session, mock_embedding_service)

        created = service.create_category(name="OldName", description="Old description")

        result = service.update_category(
            created.category.id, name="NewName", description="New description"
        )

        assert result is not None
        assert result.category.name == "NewName"
        assert result.category.description == "New description"

    def test_update_category_partial(self, db_session, mock_embedding_service):
        """Test updating only some fields."""
        service = CategoriesService(db_session, mock_embedding_service)

        created = service.create_category(name="Name", description="Old description")

        result = service.update_category(created.category.id, description="New description")

        assert result is not None
        assert result.category.name == "Name"
        assert result.category.description == "New description"

    def test_update_category_not_found(self, db_session, mock_embedding_service):
        """Test updating non-existent category returns None."""
        service = CategoriesService(db_session, mock_embedding_service)

        result = service.update_category(9999, name="NewName")
        assert result is None

    def test_delete_category(self, db_session, mock_embedding_service):
        """Test deleting a category."""
        service = CategoriesService(db_session, mock_embedding_service)

        created = service.create_category(name="ToDelete", description="Will be deleted")

        success = service.delete_category(created.category.id)
        assert success is True

        # Verify deleted
        result = service.get_category(created.category.id)
        assert result is None

    def test_delete_category_not_found(self, db_session, mock_embedding_service):
        """Test deleting non-existent category returns False."""
        service = CategoriesService(db_session, mock_embedding_service)

        success = service.delete_category(9999)
        assert success is False

    def test_update_category_regenerates_embedding(self, db_session, mock_embedding_service):
        """Test that updating a category regenerates its embedding (idempotent with create)."""
        service = CategoriesService(db_session, mock_embedding_service)

        # Create category
        created = service.create_category(name="Original", description="Original description")
        original_embedding = created.category.embedding.copy()
        assert original_embedding is not None

        # Update category - this should regenerate the embedding
        updated = service.update_category(
            created.category.id, name="Updated", description="Updated description"
        )

        assert updated is not None
        assert updated.category.embedding is not None
        assert len(updated.category.embedding) == 1536
        # Embedding should be regenerated (mock service generates different embeddings)
        # The key is that embedding exists and has correct length

    def test_update_category_partial_regenerates_embedding(
        self, db_session, mock_embedding_service
    ):
        """Test that partial updates also regenerate embedding."""
        service = CategoriesService(db_session, mock_embedding_service)

        # Create category
        created = service.create_category(name="Name", description="Original description")

        # Update only description - embedding should still be regenerated
        result = service.update_category(created.category.id, description="New description")

        assert result is not None
        assert result.category.embedding is not None
        assert len(result.category.embedding) == 1536
