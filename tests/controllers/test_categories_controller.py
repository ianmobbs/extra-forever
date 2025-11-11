"""
Tests for app/controllers/categories_controller.py
"""
import pytest
import tempfile
from pathlib import Path
from app.controllers.categories_controller import CategoriesController


@pytest.fixture
def controller():
    """Create a CategoriesController with temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = f"sqlite:///{tmp.name}"
        controller = CategoriesController(db_path=db_path)
        yield controller
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)


class TestCategoriesController:
    """Test CategoriesController class."""
    
    def test_create_category(self, controller):
        """Test creating a category through controller."""
        result = controller.create_category(
            name="Work Travel",
            description="Work-related travel receipts from airlines"
        )
        
        assert result.category.id is not None
        assert result.category.name == "Work Travel"
        assert result.category.description == "Work-related travel receipts from airlines"
    
    def test_get_category(self, controller):
        """Test retrieving a category."""
        created = controller.create_category(name="Test", description="Test category")
        
        result = controller.get_category(created.category.id)
        assert result is not None
        assert result.category.name == "Test"
    
    def test_get_category_by_name(self, controller):
        """Test retrieving a category by name."""
        controller.create_category(name="FindMe", description="Test")
        
        result = controller.get_category_by_name("FindMe")
        assert result is not None
        assert result.category.name == "FindMe"
    
    def test_list_categories(self, controller):
        """Test listing all categories."""
        controller.create_category(name="Cat1", description="First")
        controller.create_category(name="Cat2", description="Second")
        controller.create_category(name="Cat3", description="Third")
        
        categories = controller.list_categories()
        assert len(categories) == 3
    
    def test_update_category(self, controller):
        """Test updating a category."""
        created = controller.create_category(name="OldName", description="Old description")
        
        result = controller.update_category(
            created.category.id,
            name="NewName",
            description="New description"
        )
        
        assert result is not None
        assert result.category.name == "NewName"
        assert result.category.description == "New description"
    
    def test_delete_category(self, controller):
        """Test deleting a category."""
        created = controller.create_category(name="ToDelete", description="Will be deleted")
        
        success = controller.delete_category(created.category.id)
        assert success is True
        
        # Verify deleted
        result = controller.get_category(created.category.id)
        assert result is None

