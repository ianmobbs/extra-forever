"""
Categories service for orchestrating category operations.
"""
from typing import List, Optional
from dataclasses import dataclass

from models import Category
from app.managers.category_manager import CategoryManager
from app.stores.sqlite_store import SQLiteStore


@dataclass
class CategoryResult:
    """Result of a category operation."""
    category: Category


class CategoriesService:
    """Service for orchestrating category operations."""
    
    def __init__(self, store: SQLiteStore):
        self.store = store
    
    def create_category(self, name: str, description: str) -> CategoryResult:
        """
        Create a new category.
        
        Args:
            name: Category name
            description: Natural-language description of the category
            
        Returns:
            CategoryResult with the created category
        """
        session = self.store.create_session()
        try:
            manager = CategoryManager(session)
            category = manager.create(name=name, description=description)
            return CategoryResult(category=category)
        finally:
            session.close()
    
    def get_category(self, category_id: int) -> Optional[CategoryResult]:
        """
        Get a category by ID.
        
        Args:
            category_id: Category ID
            
        Returns:
            CategoryResult or None if not found
        """
        session = self.store.create_session()
        try:
            manager = CategoryManager(session)
            category = manager.get_by_id(category_id)
            if category:
                return CategoryResult(category=category)
            return None
        finally:
            session.close()
    
    def get_category_by_name(self, name: str) -> Optional[CategoryResult]:
        """
        Get a category by name.
        
        Args:
            name: Category name
            
        Returns:
            CategoryResult or None if not found
        """
        session = self.store.create_session()
        try:
            manager = CategoryManager(session)
            category = manager.get_by_name(name)
            if category:
                return CategoryResult(category=category)
            return None
        finally:
            session.close()
    
    def list_categories(self) -> List[Category]:
        """
        List all categories.
        
        Returns:
            List of all categories
        """
        session = self.store.create_session()
        try:
            manager = CategoryManager(session)
            return manager.get_all()
        finally:
            session.close()
    
    def update_category(
        self,
        category_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[CategoryResult]:
        """
        Update a category.
        
        Args:
            category_id: Category ID
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            CategoryResult or None if not found
        """
        session = self.store.create_session()
        try:
            manager = CategoryManager(session)
            category = manager.update(category_id, name=name, description=description)
            if category:
                return CategoryResult(category=category)
            return None
        finally:
            session.close()
    
    def delete_category(self, category_id: int) -> bool:
        """
        Delete a category.
        
        Args:
            category_id: Category ID
            
        Returns:
            True if deleted, False if not found
        """
        session = self.store.create_session()
        try:
            manager = CategoryManager(session)
            return manager.delete(category_id)
        finally:
            session.close()

