"""
Tests for app/services/categories_service.py
"""
import pytest
from app.services.categories_service import CategoriesService


class TestCategoriesService:
    """Test CategoriesService class."""
    
    def test_create_category(self, sqlite_store):
        """Test creating a category through service."""
        service = CategoriesService(sqlite_store)
        
        result = service.create_category(
            name="Work Travel",
            description="Work-related travel receipts from airlines"
        )
        
        assert result.category.id is not None
        assert result.category.name == "Work Travel"
        assert result.category.description == "Work-related travel receipts from airlines"
    
    def test_create_category_duplicate_raises_error(self, sqlite_store):
        """Test creating duplicate category raises error."""
        service = CategoriesService(sqlite_store)
        
        service.create_category(name="Unique", description="First")
        
        with pytest.raises(ValueError):
            service.create_category(name="Unique", description="Second")
    
    def test_get_category(self, sqlite_store):
        """Test retrieving category by ID."""
        service = CategoriesService(sqlite_store)
        
        created = service.create_category(name="Test", description="Test category")
        
        result = service.get_category(created.category.id)
        assert result is not None
        assert result.category.name == "Test"
    
    def test_get_category_not_found(self, sqlite_store):
        """Test retrieving non-existent category returns None."""
        service = CategoriesService(sqlite_store)
        
        result = service.get_category(9999)
        assert result is None
    
    def test_get_category_by_name(self, sqlite_store):
        """Test retrieving category by name."""
        service = CategoriesService(sqlite_store)
        
        service.create_category(name="FindMe", description="Test")
        
        result = service.get_category_by_name("FindMe")
        assert result is not None
        assert result.category.name == "FindMe"
    
    def test_get_category_by_name_not_found(self, sqlite_store):
        """Test retrieving category by non-existent name returns None."""
        service = CategoriesService(sqlite_store)
        
        result = service.get_category_by_name("NonExistent")
        assert result is None
    
    def test_list_categories(self, sqlite_store):
        """Test listing all categories."""
        service = CategoriesService(sqlite_store)
        
        service.create_category(name="Cat1", description="First")
        service.create_category(name="Cat2", description="Second")
        service.create_category(name="Cat3", description="Third")
        
        categories = service.list_categories()
        assert len(categories) == 3
        assert {cat.name for cat in categories} == {"Cat1", "Cat2", "Cat3"}
    
    def test_list_categories_empty(self, sqlite_store):
        """Test listing categories when none exist."""
        service = CategoriesService(sqlite_store)
        
        categories = service.list_categories()
        assert categories == []
    
    def test_update_category(self, sqlite_store):
        """Test updating a category."""
        service = CategoriesService(sqlite_store)
        
        created = service.create_category(name="OldName", description="Old description")
        
        result = service.update_category(
            created.category.id,
            name="NewName",
            description="New description"
        )
        
        assert result is not None
        assert result.category.name == "NewName"
        assert result.category.description == "New description"
    
    def test_update_category_partial(self, sqlite_store):
        """Test updating only some fields."""
        service = CategoriesService(sqlite_store)
        
        created = service.create_category(name="Name", description="Old description")
        
        result = service.update_category(
            created.category.id,
            description="New description"
        )
        
        assert result is not None
        assert result.category.name == "Name"
        assert result.category.description == "New description"
    
    def test_update_category_not_found(self, sqlite_store):
        """Test updating non-existent category returns None."""
        service = CategoriesService(sqlite_store)
        
        result = service.update_category(9999, name="NewName")
        assert result is None
    
    def test_delete_category(self, sqlite_store):
        """Test deleting a category."""
        service = CategoriesService(sqlite_store)
        
        created = service.create_category(name="ToDelete", description="Will be deleted")
        
        success = service.delete_category(created.category.id)
        assert success is True
        
        # Verify deleted
        result = service.get_category(created.category.id)
        assert result is None
    
    def test_delete_category_not_found(self, sqlite_store):
        """Test deleting non-existent category returns False."""
        service = CategoriesService(sqlite_store)
        
        success = service.delete_category(9999)
        assert success is False

