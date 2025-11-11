"""
Tests for app/managers/category_manager.py
"""
import pytest
from app.managers.category_manager import CategoryManager
from models import Category


class TestCategoryManager:
    """Test CategoryManager class."""
    
    def test_create(self, db_session):
        """Test create adds category to database."""
        manager = CategoryManager(db_session)
        
        category = manager.create(
            name="Work Travel",
            description="Work-related travel receipts from airlines"
        )
        
        assert category.id is not None
        assert category.name == "Work Travel"
        assert category.description == "Work-related travel receipts from airlines"
        
        # Verify in database
        count = db_session.query(Category).count()
        assert count == 1
    
    def test_create_duplicate_name_raises_error(self, db_session):
        """Test creating category with duplicate name raises ValueError."""
        manager = CategoryManager(db_session)
        
        manager.create(name="Unique", description="First")
        
        with pytest.raises(ValueError) as exc_info:
            manager.create(name="Unique", description="Second")
        
        assert "already exists" in str(exc_info.value)
    
    def test_get_by_id(self, db_session):
        """Test get_by_id retrieves correct category."""
        manager = CategoryManager(db_session)
        
        created = manager.create(name="Test", description="Test category")
        
        retrieved = manager.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test"
    
    def test_get_by_id_not_found(self, db_session):
        """Test get_by_id returns None for non-existent ID."""
        manager = CategoryManager(db_session)
        
        result = manager.get_by_id(9999)
        assert result is None
    
    def test_get_by_name(self, db_session):
        """Test get_by_name retrieves correct category."""
        manager = CategoryManager(db_session)
        
        manager.create(name="FindMe", description="Test")
        
        retrieved = manager.get_by_name("FindMe")
        assert retrieved is not None
        assert retrieved.name == "FindMe"
    
    def test_get_by_name_not_found(self, db_session):
        """Test get_by_name returns None for non-existent name."""
        manager = CategoryManager(db_session)
        
        result = manager.get_by_name("NonExistent")
        assert result is None
    
    def test_get_all(self, db_session):
        """Test get_all retrieves all categories."""
        manager = CategoryManager(db_session)
        
        manager.create(name="Cat1", description="First")
        manager.create(name="Cat2", description="Second")
        manager.create(name="Cat3", description="Third")
        
        all_categories = manager.get_all()
        assert len(all_categories) == 3
        assert all(isinstance(cat, Category) for cat in all_categories)
    
    def test_get_all_empty(self, db_session):
        """Test get_all returns empty list when no categories exist."""
        manager = CategoryManager(db_session)
        
        all_categories = manager.get_all()
        assert all_categories == []
    
    def test_update_name(self, db_session):
        """Test updating category name."""
        manager = CategoryManager(db_session)
        
        category = manager.create(name="OldName", description="Description")
        
        updated = manager.update(category.id, name="NewName")
        assert updated is not None
        assert updated.name == "NewName"
        assert updated.description == "Description"
    
    def test_update_description(self, db_session):
        """Test updating category description."""
        manager = CategoryManager(db_session)
        
        category = manager.create(name="Name", description="Old description")
        
        updated = manager.update(category.id, description="New description")
        assert updated is not None
        assert updated.name == "Name"
        assert updated.description == "New description"
    
    def test_update_both_fields(self, db_session):
        """Test updating both name and description."""
        manager = CategoryManager(db_session)
        
        category = manager.create(name="OldName", description="Old description")
        
        updated = manager.update(
            category.id,
            name="NewName",
            description="New description"
        )
        assert updated is not None
        assert updated.name == "NewName"
        assert updated.description == "New description"
    
    def test_update_not_found(self, db_session):
        """Test updating non-existent category returns None."""
        manager = CategoryManager(db_session)
        
        result = manager.update(9999, name="NewName")
        assert result is None
    
    def test_update_duplicate_name_raises_error(self, db_session):
        """Test updating to duplicate name raises ValueError."""
        manager = CategoryManager(db_session)
        
        cat1 = manager.create(name="First", description="First category")
        manager.create(name="Second", description="Second category")
        
        with pytest.raises(ValueError) as exc_info:
            manager.update(cat1.id, name="Second")
        
        assert "already exists" in str(exc_info.value)
    
    def test_delete(self, db_session):
        """Test deleting a category."""
        manager = CategoryManager(db_session)
        
        category = manager.create(name="ToDelete", description="Will be deleted")
        category_id = category.id
        
        success = manager.delete(category_id)
        assert success is True
        
        # Verify deleted
        retrieved = manager.get_by_id(category_id)
        assert retrieved is None
    
    def test_delete_not_found(self, db_session):
        """Test deleting non-existent category returns False."""
        manager = CategoryManager(db_session)
        
        success = manager.delete(9999)
        assert success is False
    
    def test_count(self, db_session):
        """Test count returns correct number."""
        manager = CategoryManager(db_session)
        
        assert manager.count() == 0
        
        manager.create(name="Cat1", description="First")
        manager.create(name="Cat2", description="Second")
        manager.create(name="Cat3", description="Third")
        
        assert manager.count() == 3

