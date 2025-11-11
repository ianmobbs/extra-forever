"""
Category manager for CRUD operations on Category entities.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import Category


class CategoryManager:
    """Manages CRUD operations for Category entities."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, name: str, description: str, embedding: Optional[List[float]] = None) -> Category:
        """Create a new category."""
        category = Category(name=name, description=description, embedding=embedding)
        self.session.add(category)
        try:
            self.session.commit()
            self.session.refresh(category)
            return category
        except IntegrityError:
            self.session.rollback()
            raise ValueError(f"Category with name '{name}' already exists")
    
    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Get a category by ID."""
        return self.session.query(Category).filter(Category.id == category_id).first()
    
    def get_by_name(self, name: str) -> Optional[Category]:
        """Get a category by name."""
        return self.session.query(Category).filter(Category.name == name).first()
    
    def get_all(self) -> List[Category]:
        """Get all categories."""
        return self.session.query(Category).all()
    
    def update(self, category_id: int, name: Optional[str] = None, description: Optional[str] = None, embedding: Optional[List[float]] = None) -> Optional[Category]:
        """Update a category by ID."""
        category = self.get_by_id(category_id)
        if not category:
            return None
        
        if name is not None:
            category.name = name
        if description is not None:
            category.description = description
        if embedding is not None:
            category.embedding = embedding
        
        try:
            self.session.commit()
            self.session.refresh(category)
            return category
        except IntegrityError:
            self.session.rollback()
            raise ValueError(f"Category with name '{name}' already exists")
    
    def delete(self, category_id: int) -> bool:
        """Delete a category by ID."""
        category = self.get_by_id(category_id)
        if not category:
            return False
        
        self.session.delete(category)
        self.session.commit()
        return True
    
    def count(self) -> int:
        """Count total categories in the database."""
        return self.session.query(Category).count()

